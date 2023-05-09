from rest_framework.test import APITestCase
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from six import BytesIO
from PIL import Image
import json
from chatapi.custom_methods import translate_text


def create_image(storage, filename, size=(100, 100), image_mode='RGB', image_format='PNG'):
    data = BytesIO()
    Image.new(image_mode, size).save(data, image_format)
    data.seek(0)
    if not storage:
        return data
    image_file = ContentFile(data.read())
    return storage.save(filename, image_file)

"""
class TestFileUpload(APITestCase):
    file_upload_url = "/message/file-upload"

    def test_file_upload(self):
        avatar = create_image(None, 'avatar.png')
        avatar_file = SimpleUploadedFile('front1.png', avatar.getvalue())
        data = {
            "file_upload": avatar_file
        }

        response = self.client.post(self.file_upload_url, data=data)
        result = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(result["id"], 1)
"""

class TestMessage(APITestCase):
    message_url = "/message/message"
    file_upload_url = "/message/file-upload"
    login_url = "/user/login"

    def setUp(self):
        from user_control.models import CustomUser, UserProfile

        payload = {
            "username": "sender",
            "password": "sender123",
            "email": "takadykova@edu.hse.ru"
        }

        # sender
        self.sender = CustomUser.objects._create_user(**payload)
        UserProfile.objects.create(
            first_name="sender", last_name="sender", user=self.sender, language="english")

        # login
        response = self.client.post(self.login_url, data=payload)
        result = response.json()

        self.bearer = {
            'HTTP_AUTHORIZATION': 'Bearer {}'.format(result['access'])}

        self.receiver = CustomUser.objects._create_user(
            "receiver", "receiver123", email="tanya-kta@bk.ru")
        UserProfile.objects.create(
            first_name="receiver", last_name="receiver", user=self.receiver, language="russian")
        self.receiver2 = CustomUser.objects._create_user(
            "receiver2", "receiver2123", email="ricopin@bk.ru")
        UserProfile.objects.create(
            first_name="receiver2", last_name="receiver2", user=self.receiver2, language="russian")
    
    def test_post_message(self):
        payload = {
            "sender_id": self.sender.id,
            "receiver_id": self.receiver.id,
            "message": "test message",
        }

        response = self.client.post(
            self.message_url, data=payload, **self.bearer)
        result = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(result["message"], "test message")
        self.assertEqual(result["sender"]["user"]["username"], "sender")
        self.assertEqual(result["receiver"]["user"]["username"], "receiver")
    
    def test_update_message(self):
        payload = {
            "sender_id": self.sender.id,
            "receiver_id": self.receiver.id,
            "message": "test message",
        }
        self.client.post(self.message_url, data=payload, **self.bearer)

        payload = {
            "message": "test message updated",
            "is_read": True
        }
        response = self.client.patch(
            self.message_url+"/1", data=payload, **self.bearer)
        result = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(result["message"], "test message updated")
        self.assertEqual(result["is_read"], True)

    def test_delete_message(self):
        payload = {
            "sender_id": self.sender.id,
            "receiver_id": self.receiver.id,
            "message": "test message",
        }
        self.client.post(self.message_url, data=payload, **self.bearer)

        response = self.client.delete(
            self.message_url+"/1", data=payload, **self.bearer)

        self.assertEqual(response.status_code, 204)

    def test_get_message(self):
        payload = {
            "sender_id": self.sender.id,
            "receiver_id": self.receiver.id,
            "message": "test message",
        }
        response = self.client.post(
            self.message_url, data=payload, **self.bearer)
        payload = {
            "sender_id": self.sender.id,
            "receiver_id": self.receiver2.id,
            "message": "тестовое сообщение",
        }
        response = self.client.post(
            self.message_url, data=payload, **self.bearer)

        response = self.client.get(
            self.message_url+f"?user_id={self.receiver.id}", **self.bearer)
        result = response.json()
        #print(result)

        self.assertEqual(response.status_code, 200)
