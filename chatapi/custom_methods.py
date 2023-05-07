from rest_framework import status
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.utils import timezone
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.conf import settings
import requests


class IsAuthenticatedCustom(BasePermission):
    def has_permission(self, request, view):
        from user_control.views import decodeJWT
        user = decodeJWT(request.META['HTTP_AUTHORIZATION'])
        if not user:
            return False
        request.user = user
        if request.user and request.user.is_authenticated:
            from user_control.models import CustomUser
            CustomUser.objects.filter(id=request.user.id).update(
                is_online=timezone.now())
            return True
        return False


class IsAuthenticatedOrReadCustom(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if request.user and request.user.is_authenticated:
            from user_control.models import CustomUser
            CustomUser.objects.filter(id=request.user.id).update(
                is_online=timezone.now())
            return True
        return False


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response:
        return response
    exc_list = str(exc).split("DETAIL: ")
    return Response({"error": exc_list[-1]}, status=status.HTTP_403_FORBIDDEN)

def translate_text(text, language):
    folder_id = 'https://console.cloud.yandex.ru/folders/b1gs2borf13ieg6fhg0i'

    body = {
        "targetLanguageCode": language,
        "texts": text,
        "folderId": folder_id,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {0}".format(settings.IAM_TOKEN)
    }

    response = requests.post('https://translate.api.cloud.yandex.net/translate/v2/translate',
        json = body,
        headers = headers
    )
    print(response)
