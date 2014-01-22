import unittest

from tangled.web.app import Application
from tangled.web.events import ApplicationCreated


def include(app):
    app.add_subscriber(ApplicationCreated, on_created)


def on_created(event):
    assert isinstance(event, ApplicationCreated), str(event)
    event.non_existent_attribute


class Tests(unittest.TestCase):

    def make_app(self, settings=None, parse_settings=True):
        settings = settings if settings is not None else {}
        app = Application(settings, parse_settings)
        return app

    def test_create(self):
        app = self.make_app()
        self.assertIsInstance(app, Application)
        self.assertTrue(hasattr(app, 'settings'))

    def test_create_with_settings_file(self):
        app = self.make_app('tangled.web.tests:test.ini')
        self.assertIsInstance(app, Application)
        self.assertTrue(hasattr(app, 'settings'))
        self.assertIn('b', app.settings)
        self.assertTrue(app.settings['b'])
        self.assertIn('n', app.settings)
        self.assertEqual(app.settings['n'], 1)

    def test_create_with_include(self):
        settings = {
            'tangled.app.includes': 'tangled.web.tests.test_app:include'
        }
        with self.assertRaisesRegex(AttributeError, 'non_existent_attribute'):
            self.make_app(settings)

    def test_ApplicationCreated_event_fires(self):
        settings = {
            'tangled.app.on_created': 'tangled.web.tests.test_app:on_created',
        }
        self.assertRaisesRegex(
            AttributeError, 'non_existent_attribute', self.make_app, settings)

    def test_ApplicationCreated_subscriber_added_in_include_gets_called(self):
        settings = {
            'tangled.app.includes': [include],
        }
        self.assertRaisesRegex(
            AttributeError, 'non_existent_attribute', self.make_app, settings)
