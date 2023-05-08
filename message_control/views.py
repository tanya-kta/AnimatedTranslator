from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from .serializers import GenericFileUpload, GenericFileUploadSerializer, Message, MessageAttachment, MessageSerializer
from chatapi.custom_methods import IsAuthenticatedCustom, translate_text
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings
import requests
import json


def handleRequest(serializer):
    notification = {
        "message": serializer.data.get("message"),
        "from": serializer.data.get("sender"),
        "receiver": serializer.data.get("receiver").get("id")
    }
    headers = {
        "content-Type": "application/json",
    }
    try:
        requests.post(settings.SOCKET_SERVER, json.dumps(notification), headers=headers)
    except Exception as e:
        pass
    return True


class GenericFileUploadView(ModelViewSet):
    queryset = GenericFileUpload.objects.all()
    serializer_class = GenericFileUploadSerializer


class MessageView(ModelViewSet):
    queryset = Message.objects.select_related("sender", "receiver")\
        .prefetch_related("message_attachments")
    serializer_class = MessageSerializer
    permission_classes = (IsAuthenticatedCustom, )

    def get_queryset(self):
        #from user_control.models import UserProfile, CustomUser
        data = self.request.query_params.dict()
        user_id = data.get("user_id", None)

        if user_id:
            active_user_id = self.request.user.id
            #user = CustomUser.objects.filter(id=user_id).distinct()[0]
            #language = UserProfile.objects.filter(user=user).distinct()[0].language
            #print(language)
            translated_query = self.queryset.filter(
                Q(sender_id=user_id, receiver_id=active_user_id) |
                Q(sender_id=active_user_id, receiver_id=user_id)).distinct()
            #print(translated_query)
            #translated_query[0].message = translate_text(translated_query[0].message, language)["translations"][0]["text"]
            #print(translated_query[0] == self.queryset.filter(
            #    Q(sender_id=user_id, receiver_id=active_user_id) |
            #    Q(sender_id=active_user_id, receiver_id=user_id)).distinct()[0])
               
            return translated_query
        return self.queryset

    def create(self, request, *args, **kwargs):
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True
        attachments = request.data.pop("attachments", None)

        if str(request.user.id) != str(request.data.get("sender_id", None)):
            raise Exception("Only sender can create a message")

        #print(request.data)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.data['message'] = "https://res.cloudinary.com/dhip0v8jx/image/upload/v1683574428/pug-dance_l55nty.gif"
        serializer2 = self.serializer_class(data=request.data)
        serializer2.is_valid(raise_exception=True)
        serializer2.save()

        return Response(serializer.data, status=201)

    def update(self, request, *args, **kwargs):
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True
        attachments = request.data.pop("attachments", None)
        instance = self.get_object()

        serializer = self.serializer_class(
            data=request.data, instance=instance, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        MessageAttachment.objects.filter(message_id=instance.id).delete()

        if attachments:
            MessageAttachment.objects.bulk_create([MessageAttachment(
                **attachment, message_id=serializer.data["id"]) for attachment in attachments])
            message_data = self.get_object()
            return Response(self.serializer_class(message_data).data, status=201)

        handleRequest(serializer)

        return Response(serializer.data, status=201)


class ReadMultipleMessages(APIView):
    def post(self, request):
        data = request.data.get("message_ids", None)

        Message.objects.filter(id__in=data).update(is_read=True)
        return Response("success")
