# UserResource
from django.contrib.auth.models import User
from django.test import TestCase
from tastypie.test import ResourceTestCaseMixin

from oppia.tests.utils import get_api_key,get_api_url


class UserResourceTest(ResourceTestCaseMixin, TestCase):
    fixtures = ['quiz.json', 'user.json']

    def setUp(self):
        super(UserResourceTest, self).setUp()
        self.url = '/api/v1/response/'
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

    # check get response
    def test_getResponse(self):
        resource_url = get_api_url('response', 1)
        resp = self.api_client.get(resource_url, format='json', data=self.demo_auth)
        self.assertHttpOK(resp)
        self.assertValidJSON(resp.content)

        #check response format
        response = self.deserialize(resp)
        self.assertTrue('question' in response)
        self.assertTrue('order' in response)
        self.assertTrue('title' in response)
        self.assertTrue('score' in response)
        self.assertTrue('props' in response)

    #check unauthorized user
    def test_getResponsepUnauthorized(self):
        resource_url = get_api_url('response', 1)
        self.assertHttpUnauthorized(self.api_client.get(resource_url, format='json', data=self.Unauthorized))

    #check non-existent response
    def test_getNonExistentResponse(self):
        resource_url = get_api_url('response', 900)
        resp = self.api_client.get(resource_url, format='json', data=self.demo_auth)
        self.assertHttpNotFound(resp)
