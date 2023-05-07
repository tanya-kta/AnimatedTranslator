from rest_framework.test import APITestCase
from .views import get_random, get_access_token, get_refresh_token
from .models import CustomUser, UserProfile
from message_control.tests import create_image, SimpleUploadedFile


class TestGenericFunctions(APITestCase):
    def test_get_random(self):
        rand1 = get_random(10)
        rand2 = get_random(10)
        rand3 = get_random(15)

        self.assertTrue(rand1)
        self.assertNotEqual(rand1, rand2)
        self.assertEqual(len(rand1), 10)
        self.assertEqual(len(rand3), 15)

    def test_get_access_token(self):
        payload = {
            "id": 1
        }
        token = get_access_token(payload)
        self.assertTrue(token)

    def test_refresh_token(self):
        token = get_refresh_token()
        self.assertTrue(token)


class TestAuth(APITestCase):
    login_url = "/user/login"
    register_url = "/user/register"
    refresh_url = "/user/refresh"

    def test_register(self):
        payload = {
            "username": "tanya-kta",
            "email": "takadykova@edu.hse.ru",
            "password": "tanya9911"
        }

        response = self.client.post(self.register_url, data=payload)
        self.assertEqual(response.status_code, 201)

    def test_login(self):
        payload = {
            "username": "tanya-kta",
            "email": "takadykova@edu.hse.ru",
            "password": "tanya9911"
        }

        self.client.post(self.register_url, data=payload)
        response = self.client.post(self.login_url, data=payload)
        result = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(result["access"])
        self.assertTrue(result["refresh"])

    def test_refresh(self):
        payload = {
            "username": "tanya-kta",
            "email": "takadykova@edu.hse.ru",
            "password": "tanya9911"
        }

        self.client.post(self.register_url, data=payload)
        response = self.client.post(self.login_url, data=payload)
        refresh = response.json()['refresh']

        self.assertEqual(response.status_code, 200)
        self.assertTrue(refresh)

        response = self.client.post(self.refresh_url, data={"refresh": refresh})
        result = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(result["access"])
        self.assertTrue(result["refresh"])


class TestUserInfo(APITestCase):
    profile_url = "/user/profile"
    file_upload_url = "/message/file-upload"
    login_url = "/user/login"

    def setUp(self):
        payload = {
            "username": "takadykova",
            "password": "takadykova123",
            "email": "takadykova@edu.hse.ru"
        }

        self.user = CustomUser.objects._create_user(**payload)

        response = self.client.post(self.login_url, data=payload)
        result = response.json()

        self.bearer = {
            'HTTP_AUTHORIZATION': 'Bearer {}'.format(result['access'])}

    def test_post_user_profile(self):

        payload = {
            "user_id": self.user.id,
            "first_name": "Tanya",
            "last_name": "Kadykova",
            "language": "russian"
        }

        response = self.client.post(
            self.profile_url, data=payload, **self.bearer)
        result = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(result["first_name"], "Tanya")
        self.assertEqual(result["last_name"], "Kadykova")
        self.assertEqual(result["user"]["username"], "takadykova")

    def test_post_user_profile_with_profile_picture(self):
        avatar = create_image(None, 'avatar.png')
        avatar_file = SimpleUploadedFile('front.png', avatar.getvalue())
        data = {
            "file_upload": avatar_file
        }

        response = self.client.post(
            self.file_upload_url, data=data, **self.bearer)
        result = response.json()

        payload = {
            "user_id": self.user.id,
            "first_name": "Tanya",
            "last_name": "Kadykova",
            "language": "russian",
            "profile_picture_id": result["id"]
        }

        response = self.client.post(
            self.profile_url, data=payload, **self.bearer)
        result = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(result["first_name"], "Tanya")
        self.assertEqual(result["last_name"], "Kadykova")
        self.assertEqual(result["user"]["username"], "takadykova")
        self.assertEqual(result["profile_picture"]["id"], 1)

    def test_update_user_profile(self):
        payload = {
            "user_id": self.user.id,
            "first_name": "Tanya",
            "last_name": "Kadykova",
            "language": "russian"
        }

        response = self.client.post(
            self.profile_url, data=payload, **self.bearer)
        result = response.json()

        payload = {
            "first_name": "Tatiana",
            "last_name": "Kad",
        }

        response = self.client.patch(
            self.profile_url + f"/{result['id']}", data=payload, **self.bearer)
        result = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["first_name"], "Tatiana")
        self.assertEqual(result["last_name"], "Kad")
        self.assertEqual(result["user"]["username"], "takadykova")

    def test_user_search(self):

        UserProfile.objects.create(user=self.user, first_name="Tanya", last_name="Kadykova")

        user2 = CustomUser.objects._create_user(
            username="tester1", password="tester1123", email="tanya-kta@bk.ru")
        UserProfile.objects.create(user=user2, first_name="tester1", last_name="tester1")

        user3 = CustomUser.objects._create_user(
            username="tester2", password="tester2123", email="ricopin@bk.ru")
        UserProfile.objects.create(user=user3, first_name="tester2", last_name="tester2")

        url = self.profile_url + "?keyword=Tanya Kadykova"

        response = self.client.get(url, **self.bearer)
        result = response.json()["results"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(result), 1)

        url = self.profile_url + "?keyword=tester"

        response = self.client.get(url, **self.bearer)
        result = response.json()["results"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["user"]["username"], "tester2")
