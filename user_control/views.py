import jwt
import requests
from django.http import HttpResponse

from .models import JwtModel, CustomUser, Favorite
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import random
import string
from rest_framework.views import APIView
from .serializers import LoginSerializer, RegisterSerializer, RefreshSerializer, UserProfileSerializer, UserProfile, FavoriteSerializer
from django.contrib.auth import authenticate
from rest_framework.response import Response
from .authentication import Authentication
from chatapi.custom_methods import IsAuthenticatedCustom
from rest_framework.viewsets import ModelViewSet
import re
import json
from django.db.models import Q, Count, Subquery, OuterRef

from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from .tokens import account_activation_token
from django.core.mail import send_mail, EmailMessage
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string


def get_random(length):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def get_access_token(payload):
    return jwt.encode(
        {"exp": datetime.now() + timedelta(minutes=5), **payload},
        settings.SECRET_KEY,
        algorithm="HS256"
    )


def get_refresh_token():
    return jwt.encode(
        {"exp": datetime.now() + timedelta(days=365), "data": get_random(10)},
        settings.SECRET_KEY,
        algorithm="HS256"
    )


def decodeJWT(bearer):
    if not bearer:
        return None

    token = bearer[7:]
    decoded = jwt.decode(token, key=settings.SECRET_KEY, algorithms=["HS256"])
    if decoded:
        try:
            return CustomUser.objects.get(id=decoded["user_id"])
        except Exception:
            return None


class LoginView(APIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'])

        if not user:
            return Response({"error": "Invalid username or password"}, status="400")
        if not user.is_active:
            return Response({"error": "Email is not verified"}, status="433")

        JwtModel.objects.filter(user_id=user.id).delete()

        access = get_access_token({"user_id": user.id})
        refresh = get_refresh_token()
        JwtModel.objects.create(
            user_id=user.id, access=access,
            refresh=refresh
        )
        notification = {
            "access": access,
            "refresh": refresh
        }
        headers = {
            "content-Type": "application/json",
        }
        try:
            requests.post(settings.SOCKET_SERVER, json.dumps(notification), headers=headers)
        except Exception as e:
            pass
        return Response({"access": access, "refresh": refresh})


class RegisterView(APIView):
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        CustomUser.objects._create_user(**serializer.validated_data)
        user = CustomUser.objects.get(email=serializer.validated_data["email"])

        current_site = get_current_site(request)
        mail_subject = 'Activate your account.'
        message = render_to_string('email_template.html', {
            #'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.id)),
            'token': account_activation_token.make_token(user),
        })
        to_email = serializer.validated_data["email"]
        email = EmailMessage(
            mail_subject,
            message,
            'takadykova@edu.hse.ru',
            [to_email],
        )

        #email.fail_silently = True
        email.send()

        #send_mail(mail_subject, message, 'takadykova@edu.hse.ru', [to_email])
        return Response({"success": "Please confirm your email address to complete the registration",
                         "message": message,
                         "to_email": to_email}, status=201)


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(id=uid)
    except Exception as e:
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    else:
        return HttpResponse('Activation link is invalid!')


class RefreshView(APIView):
    serializer_class = RefreshSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            active_jwt = JwtModel.objects.get(refresh=serializer.validated_data["refresh"])
        except ObjectDoesNotExist:
            return Response({"error": "refresh token not found"}, status="400")
        if not Authentication.verify_token(serializer.validated_data["refresh"]):
            return Response({"error": "Token is invalid or has expired"})

        access = get_access_token({"user_id": active_jwt.user.id})
        refresh = get_refresh_token()

        active_jwt.access = access
        active_jwt.refresh = refresh
        active_jwt.save()

        return Response({"access": access, "refresh": refresh})


class UserProfileView(ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticatedCustom, )

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset

        data = self.request.query_params.dict()
        data.pop("page", None)
        keyword = data.pop("keyword", None)

        if keyword:
            search_fields = (
                "user__username", "first_name", "last_name", "user__email"
            )
            query = self.get_query(keyword, search_fields)
            try:
                return self.queryset.filter(query).filter(**data).exclude(
                    Q(user_id=self.request.user.id) |
                    Q(user__is_superuser=True)
                ).annotate(
                    fav_count=Count(self.user_fav_query(self.request.user))
                ).order_by("-fav_count")
            except Exception as e:
                raise Exception(e)
        result = self.queryset.filter(**data).exclude(
            Q(user_id=self.request.user.id) |
            Q(user__is_superuser=True)
        ).annotate(
            fav_count=Count(self.user_fav_query(self.request.user))
        ).exclude(
            Q(fav_count=0)
        )
        return result

    @staticmethod
    def user_fav_query(user):
        try:
            return user.user_favorites.favorite.filter(id=OuterRef("user_id")).values("pk")
        except Exception:
            return []

    @staticmethod
    def get_query(query_string, search_fields):
        query = None
        terms = UserProfileView.normalize_query(query_string)
        for term in terms:
            or_query = None
            for field_name in search_fields:
                q = Q(**{"%s__icontains" % field_name: term})
                if or_query is None:
                    or_query = q
                else:
                    or_query = or_query | q
            if query is None:
                query = or_query
            else:
                query = query & or_query
        return query

    @staticmethod
    def normalize_query(query_string, findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                        normspace=re.compile(r'\s{2,}').sub):
        return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]


class MeView(APIView):
    permission_classes = (IsAuthenticatedCustom, )
    serializer_class = UserProfileSerializer

    def get(self, request):
        data = {}
        try:
            data = self.serializer_class(request.user.user_profile).data
        except Exception:
            data = {
                "user": {
                    "id": request.user.id
                }
            }
        headers = {
            "content-Type": "application/json",
        }
        try:
            requests.post(settings.SOCKET_SERVER, data.json(), headers=headers)
        except Exception as e:
            pass
        return Response(data, status=200)


class LogoutView(APIView):
    permission_classes = (IsAuthenticatedCustom, )

    def get(self, request):
        user_id = request.user.id

        JwtModel.objects.filter(user_id=user_id).delete()

        return Response("logged out successfully", status=200)


class UpdateFavoriteView(APIView):
    permission_classes = (IsAuthenticatedCustom,)
    serializer_class = FavoriteSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            favorite_user = CustomUser.objects.get(id=serializer.validated_data["favorite_id"])
        except Exception:
            raise Exception("Favorite user does not exist")

        try:
            fav = request.user.user_favorites
        except Exception:
            fav = Favorite.objects.create(user_id=request.user.id)

        favorite = fav.favorite.filter(id=favorite_user.id)
        print(favorite)
        if favorite:
            fav.favorite.remove(favorite_user)
            return Response("removed")

        fav.favorite.add(favorite_user)
        return Response("added")


class CheckIsFavoriteView(APIView):
    permission_classes = (IsAuthenticatedCustom,)

    def get(self, request, *args, **kwargs):
        favorite_id = kwargs.get("favorite_id", None)
        try:
            favorite = request.user.user_favorites.favorite.filter(id=favorite_id)
            if favorite:
                return Response(True)
            return Response(False)
        except Exception:
            return Response(False)
