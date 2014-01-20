import unittest

from tangled.web.resource.mounted import MountedResource


class TestMountedResouce(unittest.TestCase):

    def test_path_parsing(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource('test', None, path)

        info = mr.urlvars_info
        self.assertEqual(info['path'], {'regex': '[\w-]+', 'converter': str})
        self.assertEqual(info['name'], {'regex': '[a-z]{3}', 'converter': str})
        self.assertEqual(info['id'], {'regex': '\d+', 'converter': int})
        self.assertEqual(info['format'], {'regex': '[a-z]+', 'converter': str})

        format_string = mr.format_string
        self.assertEqual(format_string, '/{path}{name}/{id}.{format};extra')

    def test_format_path(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource('test', None, path)
        self.assertEqual(
            mr.format_path(path='somewhere', name='bob', id=13, format='json'),
            '/somewherebob/13.json;extra')

    def test_format_path_unknown_var(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource('test', None, path)
        with self.assertRaises(ValueError):
            mr.format_path(pat='somewhere', name='bob', id=13, format='json')

    def test_format_path_bad_value(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource('test', None, path)
        with self.assertRaises(ValueError):
            mr.format_path(path='somewhere', name='bob', id='x', format='json')
