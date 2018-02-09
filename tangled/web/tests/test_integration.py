import copy
import unittest

from webtest import TestApp

from tangled.web import Application, Resource


class Users:

    data = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'},
    ]

    @classmethod
    def get(cls, id, default=None):
        for user in cls.data:
            if user['id'] == id:
                return user
        return default


class UserResource(Resource):

    def GET(self, id: int):
        user = Users.get(id)
        if user is None:
            self.request.abort(404)
        return user

    def PUT(self, id: int, *, name):
        user = self.GET(id)
        user['name'] = name
        return user

    def PATCH(self, id: int, *, name=None):
        user = self.GET(id)
        if name is not None:
            user['name'] = name
        return user

    def greet(self, id: int, *, greeting='Hello'):
        user = self.GET(id)
        return {
            'user': user,
            'greeting': greeting,
        }


class TestIntegration(unittest.TestCase):

    def setUp(self):
        app = Application('tangled.web.tests:test.ini')
        app.mount_resource('user', UserResource, '/users/<id>')
        self.app = TestApp(app)
        self._original_data = copy.deepcopy(Users.data)

    def tearDown(self):
        Users.data = self._original_data

    def test_get(self):
        self.assertEqual(Users.get(1)['name'], 'Alice')
        response = self.app.get('/users/1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Alice')
        self.assertEqual(Users.get(1)['name'], 'Alice')

    def test_put(self):
        self.assertEqual(Users.get(2)['name'], 'Bob')
        response = self.app.put('/users/2', params={'name': 'Bobby'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Bobby')
        self.assertEqual(Users.get(2)['name'], 'Bobby')

    def test_patch(self):
        self.assertEqual(Users.get(2)['name'], 'Bob')
        response = self.app.patch('/users/2', params={'name': 'Bobby'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Bobby')
        self.assertEqual(Users.get(2)['name'], 'Bobby')

    def test_patch_json(self):
        self.assertEqual(Users.get(2)['name'], 'Bob')
        response = self.app.patch_json('/users/2', params={'name': 'Bobby'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Bobby')
        self.assertEqual(Users.get(2)['name'], 'Bobby')
