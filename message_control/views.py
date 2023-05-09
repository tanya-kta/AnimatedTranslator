from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from .serializers import GenericFileUpload, GenericFileUploadSerializer, Message, MessageAttachment, MessageSerializer
from chatapi.custom_methods import IsAuthenticatedCustom, translate_text
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings
import requests
import json
import paralleldots
import operator


def getEmotionGif(text):
    emotions = paralleldots.emotion(text)["emotion"]
    emotion = max(emotions.items(), key=operator.itemgetter(1))[0]
    gifs = {
        "Sad": "https://i.gifer.com/9k4y.gif",
        "Excited": "https://i.gifer.com/IsIM.gif",
        "Angry": "https://i.gifer.com/Odc2.gif",
        "Bored": "https://i.gifer.com/cjv.gif",
        "Fear": "https://i.gifer.com/513W.gif",
        "Happy": "https://i.gifer.com/52qY.gif"
    }
    return gifs[emotion]


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
        data = self.request.query_params.dict()
        user_id = data.get("user_id", None)

        if user_id:
            active_user_id = self.request.user.id
            return self.queryset.filter(
                Q(sender_id=user_id, receiver_id=active_user_id) |
                Q(sender_id=active_user_id, receiver_id=user_id)).distinct()
        return self.queryset

    def list(self, request, *args, **kwargs):
        from user_control.models import UserProfile, CustomUser
        data = self.request.query_params.dict()
        user_id = data.get("user_id", None)
        user = CustomUser.objects.filter(id=user_id).distinct()[0]
        language = UserProfile.objects.filter(user=user).distinct()[0].language

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = serializer.data
            for item in result:
                if item["message"][0:4] != "http":
                    item["message"] = translate_text(item["message"], language)
            return self.get_paginated_response(result)

        serializer = self.get_serializer(queryset, many=True)
        result = serializer.data
        for item in result:
            if item["message"][0:4] != "http":
                item["message"] = translate_text(item["message"], language)
        return Response(result)

    def create(self, request, *args, **kwargs):
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True
        request.data.pop("attachments", None)

        if str(request.user.id) != str(request.data.get("sender_id", None)):
            raise Exception("Only sender can create a message")

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        if request.data["message"][0:4] != "http":
            request.data["message"] = getEmotionGif(translate_text(request.data["message"], "english"))
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
