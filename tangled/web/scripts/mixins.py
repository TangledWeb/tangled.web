from tangled.decorators import cached_property
from tangled.util import load_object

from .actions import SettingsAction, SettingsFileAction


class AppMixin:

    def __init__(self, parser, args):
        app_factory = self.args.app_factory
        if app_factory is None:
            app_factory = self.settings.get('factory', None)
            if app_factory is None:
                parser.error(
                    '\n    An app factory must be specified via --app-factory or factory setting.'
                    '\n    Did you specify a settings file via -f?'
                    '\n    If so, does it contain an [app] section with a factory setting?')
        self.args.app_factory = load_object(app_factory, 'make_app')

    @classmethod
    def configure(cls, parser):
        parser.add_argument('-a', '--app-factory', default=None)
        parser.add_argument(
            '-f', '--settings-file', dest='settings_from_file',
            action=SettingsFileAction, default={})
        parser.add_argument(
            '-s', '--settings', dest='settings_from_argv', nargs='*',
            action=SettingsAction, default={},
            help='Additional settings as key=val pairs')

    @cached_property
    def settings(self):
        settings = {}
        settings.update(self.args.settings_from_file)
        settings.update(self.args.settings_from_argv)
        return settings

    def make_app(self):
        return self.args.app_factory(self.settings)
