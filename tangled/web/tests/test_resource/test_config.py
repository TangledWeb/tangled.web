import unittest

import venusian

from tangled.web import Application, config as config
from tangled.web import Resource as BaseResource
from tangled.web.resource.config import Config



class TestConfig(unittest.TestCase):

    def setUp(self):
        self.app = Application({})

        class _config(config):

            _callbacks = set()

            def __call__(self, wrapped):
                value = super().__call__(wrapped)
                for v in value.__venusian_callbacks__['tangled']:
                    self._callbacks.add(v[0])
                return value

        self.config = _config

    def _scan(self, cls):
        scanner = venusian.Scanner(app=self.app)
        for callback in self.config._callbacks:
            callback(scanner, cls.__name__, cls)

    def test_no_args_raises_TypeError(self):
        with self.assertRaises(TypeError):
            self.config('*/*')(type('Resource', (), {}))

    def test_no_defaults(self):

        class Resource(BaseResource):

            @self.config('text/html', status=303)
            def GET(self):
                pass

        self._scan(Resource)

        resource = Resource(None, None)
        info = Config.for_resource(self.app, resource, 'GET', 'text/html')
        self.assertIsNone(info.type)
        self.assertEqual(info.status, 303)
        self.assertEqual(info.response_attrs, {})
        self.assertEqual(info.representation_args, {})

    def test_defaults(self):

        @self.config('*/*', status=303)
        class Resource(BaseResource):

            def GET(self):
                pass

        self._scan(Resource)

        resource = Resource(None, None)
        info = Config.for_resource(self.app, resource, 'GET', 'text/html')
        self.assertIsNone(info.type)
        self.assertEqual(info.status, 303)
        self.assertEqual(info.response_attrs, {})
        self.assertEqual(info.representation_args, {})

    def test_override_defaults(self):
        @self.config(
            '*/*', type='no_content', status=301,
            response_attrs={'status': 204})
        class Resource(BaseResource):

            @self.config('*/*', status=302)
            @self.config(
                'application/json', status=303, response_attrs={'x': 'x'})
            @self.config('text/html', type=None, response_attrs={})
            def GET(self):
                pass

        self._scan(Resource)

        resource = Resource(None, None)
        info = Config.for_resource(self.app, resource, 'GET', 'text/html')
        self.assertIsNone(info.type)
        self.assertEqual(info.status, 302)
        self.assertEqual(info.response_attrs, {})
        self.assertEqual(info.representation_args, {})

        resource = Resource(None, None)
        info = Config.for_resource(
            self.app, resource, 'GET', 'application/json')
        self.assertEqual(info.type, 'no_content')
        self.assertEqual(info.status, 303)
        self.assertEqual(info.response_attrs, {'x': 'x'})
        self.assertEqual(info.representation_args, {})

    def test_add_arg(self):

        class Resource(BaseResource):

            def GET(self):
                pass

        with self.assertRaises(TypeError):
            self._scan(self.config('*/*', xxx=True)(Resource))

        self.app.add_config_field('*/*', 'xxx', False)
        self._scan(self.config('*/*', xxx=True)(Resource))

        resource = Resource(None, None)
        info = Config.for_resource(self.app, resource, 'GET', 'text/html')
        self.assertTrue(hasattr(info, 'xxx'))
        self.assertTrue(info.xxx)
