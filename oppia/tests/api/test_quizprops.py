# UserResource
from django.contrib.auth.models import User
from django.test import TestCase
from tastypie.test import ResourceTestCaseMixin

from oppia.tests.utils import get_api_key,get_api_url


class UserResourceTest(ResourceTestCaseMixin, TestCase):
    fixtures = ['quiz.json', 'user.json']

    def setUp(self):
        super(UserResourceTest, self).setUp()
        self.url = '/api/v1/quizprops/'
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

    # check get prop
    def test_getProp(self):
        resource_url = get_api_url('quizprops', 1)
        resp = self.api_client.get(resource_url, format='json', data=self.demo_auth)
        self.assertHttpOK(resp)
        self.assertValidJSON(resp.content)

        #check prop format
        prop = self.deserialize(resp)
        self.assertTrue('name' in prop)
        self.assertTrue('value' in prop)
        self.assertTrue('quiz' in prop)

    #check unauthorized user
    def test_getPropUnauthorized(self):
        resource_url = get_api_url('quizprops', 1)
        self.assertHttpUnauthorized(self.api_client.get(resource_url, format='json', data=self.Unauthorized))

    #check non-existent prop
    def test_getNonExistentProp(self):
        resource_url = get_api_url('quizprops', 150)
        resp = self.api_client.get(resource_url, format='json', data=self.demo_auth)
        self.assertHttpNotFound(resp)
