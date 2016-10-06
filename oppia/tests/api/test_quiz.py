# UserResource
from django.contrib.auth.models import User
from django.test import TestCase
from tastypie.test import ResourceTestCaseMixin

from oppia.tests.utils import get_api_key,get_api_url


class UserResourceTest(ResourceTestCaseMixin, TestCase):
    fixtures = ['user.json', 'oppia.json', 'quiz.json']

    def setUp(self):
        super(UserResourceTest, self).setUp()
        self.url = '/api/v1/user/'
        user = User.objects.get(username='demo')
        self.valid_api_key = get_api_key(user=user)
        self.demo_auth = {
            'username': 'demo',
            'api_key': get_api_key(user=user).key
        }
        self.Unauthorized = {
        'username': 'demo123',
            'api_key': get_api_key(user=user).key
        }

    # check get not allowed
    def test_get_invalid(self):
        self.assertHttpMethodNotAllowed(self.api_client.get(self.url, format='json'))

    # check valid login
    def test_valid_login(self):
        data = {
            'username': 'demo',
            'password': 'password'
        }
        resp = self.api_client.post(self.url, format='json', data=data)
        self.assertHttpCreated(resp)
        self.assertValidJSON(resp.content)

        # check return data
        response_data = self.deserialize(resp)

        # check that the api key exists and is the correct one
        self.assertTrue('api_key' in response_data)
        api_key = response_data['api_key']
        self.assertEqual(api_key, self.valid_api_key.key)

        self.assertTrue('points' in response_data)
        self.assertTrue('badges' in response_data)
        # check it doesn't contain the password
        self.assertFalse('password' in response_data)

    # check no username
    def test_no_username(self):
        data = {
            'password': 'demo'
        }
        resp = self.api_client.post(self.url, format='json', data=data)
        self.assertHttpBadRequest(resp)
        self.assertValidJSON(resp.content)
        response_data = self.deserialize(resp)
        self.assertTrue('error' in response_data)

    # check no password
    def test_no_password(self):
        data = {
            'username': 'user',
        }
        resp = self.api_client.post(self.url, format='json', data=data)
        self.assertHttpBadRequest(resp)
        self.assertValidJSON(resp.content)
        response_data = self.deserialize(resp)
        self.assertTrue('error' in response_data)

    # check no username or password
    def test_no_username_password(self):
        data = {}
        resp = self.api_client.post(self.url, format='json', data=data)
        self.assertHttpBadRequest(resp)
        self.assertValidJSON(resp.content)
        response_data = self.deserialize(resp)
        self.assertTrue('error' in response_data)

    # check invalid password
    def test_invalid_password(self):
        data = {
            'username': 'user',
            'password': 'demo123'
        }
        resp = self.api_client.post(self.url, format='json', data=data)
        self.assertHttpBadRequest(resp)
        self.assertValidJSON(resp.content)
        response_data = self.deserialize(resp)
        self.assertTrue('error' in response_data)
    
    # check get quiz
    def test_getQuiz(self):
        resource_url = get_api_url('quiz', 1)
        resp = self.api_client.get(resource_url, format='json', data=self.demo_auth)
        self.assertHttpOK(resp)
        self.assertValidJSON(resp.content)

        #check quiz format
        quiz = self.deserialize(resp)
        self.assertTrue('title' in quiz)
        self.assertTrue('description' in quiz)
        self.assertTrue('questions' in quiz)
        self.assertTrue('props' in quiz)

    #check get unauthorized
    def test_getQuizUnauthorized(self):
        resource_url = get_api_url('quiz', 1)
        self.assertHttpUnauthorized(self.api_client.get(resource_url, format='json', data=self.Unauthorized))

    #check non-exitent quiz
    def test_getNonExistentQuiz(self):
        resource_url = get_api_url('quiz', 30)
        resp = self.api_client.get(resource_url, format='json', data=self.demo_auth)
        self.assertHttpNotFound(resp)

