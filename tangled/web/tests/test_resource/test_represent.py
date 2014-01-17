import unittest

import venusian

from tangled.web import Application, config
from tangled.web import Resource as BaseResource


class TestRepresent(unittest.TestCase):

    def setUp(self):
        config.callbacks = []
        self.app = Application({
            'tangled.app.csrf.enabled': False,
        })

    def _scan(self, cls):
        scanner = venusian.Scanner(app=self.app)
        for callback in config.callbacks:
            callback(scanner, cls.__name__, cls)

    def test_no_args_raises_TypeError(self):
        with self.assertRaises(TypeError):
            config('*/*')(type('Resource', (), {}))

    def test_no_defaults(self):

        class Resource(BaseResource):

            @config('text/html', status=303)
            def GET(self):
                pass

        self._scan(Resource)

        resource = Resource(None, None)
        info = self.app.get_representation_info(resource, 'GET', 'text/html')
        self.assertIsNone(info.type)
        self.assertEqual(info.status, 303)
        self.assertEqual(info.response_attrs, {})
        self.assertEqual(info.representation_args, {})

    def test_defaults(self):

        @config('*/*', status=303)
        class Resource(BaseResource):

            def GET(self):
                pass

        self._scan(Resource)

        resource = Resource(None, None)
        info = self.app.get_representation_info(resource, 'GET', 'text/html')
        self.assertIsNone(info.type)
        self.assertEqual(info.status, 303)
        self.assertEqual(info.response_attrs, {})
        self.assertEqual(info.representation_args, {})

    def test_override_defaults(self):
        @config(
            '*/*', type='no_content', status=301,
            response_attrs={'status': 204})
        class Resource(BaseResource):

            @config('*/*', status=302)
            @config(
                'application/json', status=303, response_attrs={'x': 'x'})
            @config('text/html', type=None, response_attrs={})
            def GET(self):
                pass

        self._scan(Resource)

        resource = Resource(None, None)
        info = self.app.get_representation_info(resource, 'GET', 'text/html')
        self.assertIsNone(info.type)
        self.assertEqual(info.status, 302)
        self.assertEqual(info.response_attrs, {})
        self.assertEqual(info.representation_args, {})

        resource = Resource(None, None)
        info = self.app.get_representation_info(
            resource, 'GET', 'application/json')
        self.assertEqual(info.type, 'no_content')
        self.assertEqual(info.status, 303)
        self.assertEqual(info.response_attrs, {'x': 'x'})
        self.assertEqual(info.representation_args, {})

    def test_add_arg(self):

        class Resource(BaseResource):

            def GET(self):
                pass

        with self.assertRaises(TypeError):
            self._scan(config('*/*', xxx=True)(Resource))

        self.app.add_representation_info_field('*/*', 'xxx', False)
        self._scan(config('*/*', xxx=True)(Resource))

        resource = Resource(None, None)
        info = self.app.get_representation_info(resource, 'GET', 'text/html')
        self.assertTrue(hasattr(info, 'xxx'))
        self.assertTrue(info.xxx)
