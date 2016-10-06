# UserResource
from django.contrib.auth.models import User
from django.test import TestCase
from tastypie.test import ResourceTestCaseMixin

from oppia.tests.utils import get_api_key,get_api_url


class UserResourceTest(ResourceTestCaseMixin, TestCase):
    fixtures = ['quiz.json', 'user.json']

    def setUp(self):
        super(UserResourceTest, self).setUp()
        self.url = '/api/v1/quizquestion/'
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

    # check get question
    def test_getQuestion(self):
        resource_url = get_api_url('question', 1)
        resp = self.api_client.get(resource_url, format='json', data=self.demo_auth)
        self.assertHttpOK(resp)
        self.assertValidJSON(resp.content)

        #check question format
        question = self.deserialize(resp)
        self.assertTrue('title' in question)
        self.assertTrue('type' in question)
        self.assertTrue('responses' in question)
        self.assertTrue('props' in question)

    #check unauthorized user
    def test_getQuestionUnauthorized(self):
        resource_url = get_api_url('question', 1)
        self.assertHttpUnauthorized(self.api_client.get(resource_url, format='json', data=self.Unauthorized))

    #check non-existent question
    def test_getNonExistentQuestion(self):
        resource_url = get_api_url('question', 400)
        resp = self.api_client.get(resource_url, format='json', data=self.demo_auth)
        self.assertHttpNotFound(resp)
