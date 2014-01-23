import unittest

from tangled.web import Application
from tangled.web.handlers import resource_finder
from tangled.web.resource.mounted import MountedResource


class TestMountedResouce(unittest.TestCase):

    def setUp(self):
        self.app = Application({})

    def test_path_parsing(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource(self.app, 'test', None, path)

        info = mr.urlvars_info
        self.assertEqual(info['path'], {'regex': '[\w-]+', 'converter': str})
        self.assertEqual(info['name'], {'regex': '[a-z]{3}', 'converter': str})
        self.assertEqual(info['id'], {'regex': '\d+', 'converter': int})
        self.assertEqual(info['format'], {'regex': '[a-z]+', 'converter': str})

        format_string = mr.format_string
        self.assertEqual(format_string, '/{path}{name}/{id}.{format};extra')

    def test_format_path(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource(self.app, 'test', None, path)
        self.assertEqual(
            mr.format_path(path='somewhere', name='bob', id=13, format='json'),
            '/somewherebob/13.json;extra')

    def test_format_path_unknown_var(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource(self.app, 'test', None, path)
        with self.assertRaises(ValueError):
            mr.format_path(pat='somewhere', name='bob', id=13, format='json')

    def test_format_path_bad_value(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource(self.app, 'test', None, path)
        with self.assertRaises(ValueError):
            mr.format_path(path='somewhere', name='bob', id='x', format='json')

    def test_add_slash(self):
        path = '/some/dir/'
        mr = MountedResource(self.app, 'test', None, path)
        self.assertTrue(mr.add_slash)
        self.assert_(mr.match('GET', '/some/dir/'))
        self.assert_(mr.match('GET', '/some/dir'))
        self.assertEqual(mr.format_path(), '/some/dir/')

    def test_add_slash_redirect(self):
        app = Application({})
        factory = lambda *args: type('Resource', (), {'GET': None})
        app.mount_resource('test', factory, '/some/dir', add_slash=True)

        # Should not redirect
        next_handler = lambda app_, request_: 'NEXT'
        request = app.make_blank_request('/some/dir/')
        self.assertEqual(resource_finder(app, request, next_handler), 'NEXT')

        # Should redirect
        request = app.make_blank_request('/some/dir')
        try:
            resource_finder(app, request, next_handler)
        except Exception as exc:
            self.assertTrue(exc.status.startswith('3'))
            self.assertTrue(exc.location.endswith('/some/dir/'))
