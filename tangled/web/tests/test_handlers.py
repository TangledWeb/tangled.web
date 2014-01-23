import unittest

from webob.exc import HTTPNotFound, HTTPMethodNotAllowed, _HTTPMove

from tangled.web import Application
from tangled.web import handlers


class TestResource:

    def __init__(self, app, request, name, urlvars):
        pass

    def GET(self):
        pass

    def my_method(self):
        pass


class TestResourceFinder(unittest.TestCase):

    def setUp(self):
        app = Application({})
        app.mount_resource('test', TestResource, '/test')
        self.app = app

    def test_resource_finder(self):
        next_handler = lambda app, req: setattr(req, 'test_attr', app)
        request = self.app.make_blank_request('/test')
        handlers.resource_finder(self.app, request, next_handler)
        self.assertTrue(hasattr(request, 'resource'))
        self.assertTrue(hasattr(request, 'test_attr'))
        self.assertIs(request.test_attr, self.app)

    def test_unregistered_path_raises_404(self):
        request = self.app.make_blank_request('/unregistered')
        with self.assertRaises(HTTPNotFound):
            handlers.resource_finder(self.app, request, lambda a, r: None)

    def test_missing_method_raises_405(self):
        request = self.app.make_blank_request('/test', method='POST')
        with self.assertRaises(HTTPMethodNotAllowed):
            handlers.resource_finder(self.app, request, lambda a, r: None)

    def test_add_slash(self):
        self.app.mount_resource('slash', TestResource, '/slash/')
        # No redirect
        request = self.app.make_blank_request('/slash/')
        handlers.resource_finder(self.app, request, lambda a, r: None)
        # Redirect to slash
        request = self.app.make_blank_request('/slash')
        with self.assertRaises(_HTTPMove) as cm:
            handlers.resource_finder(self.app, request, lambda a, r: None)
        self.assertEqual(cm.exception.location, 'http://localhost/slash/')

    def test_custom_method_name(self):
        self.app.mount_resource(
            'my_method', TestResource, '/my_method', method_name='my_method')
        request = self.app.make_blank_request('/my_method')
        handlers.resource_finder(self.app, request, lambda a, r: None)
        self.assertTrue(hasattr(request, 'resource'))
        self.assertEqual(request.resource_method, 'my_method')
