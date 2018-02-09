from runcommands import command, ArgConfig as Arg
from runcommands.command import Command
from runcommands.util import abort, include

import tangled.commands
from tangled.util import load_object
from tangled.web import make_app_settings, Resource


include('tangled.commands', exclude=['shell'])


class AppCommand(Command):

    arg_config = {
        'app_factory': Arg(help='App factory'),
        'settings_file': Arg(short_option='-f', help='Settings file'),
        'settings': Arg(short_option='-s', help='Additional settings'),
    }

    def make_app(self, app_factory, settings_file, settings):
        settings = self.make_settings(settings_file, settings)
        if app_factory is None:
            app_factory = settings.get('factory')
            if app_factory is None:
                abort(1, (
                    'An app factory must be specified via the factory setting '
                    'or using the --factory option.'
                    '\nDid you specify a settings file via --settings-file?'
                    '\nIf so, does it contain an [app] section with a factory setting?'
                ))
        app_factory = load_object(app_factory, 'make_app')
        app = app_factory(settings)
        return app

    def make_settings(self, settings_file, settings):
        if settings_file:
            return make_app_settings(settings_file, extra=settings)
        return make_app_settings(settings)


@command
class Shell(AppCommand):

    def implementation(
            self, config,
            shell_: Arg(choices=('bpython', 'ipython', 'python')) = 'bpython',
            locals_: 'Pass additional shell locals using name=package.module:object syntax' = {},
            app_factory=None, settings_file=None, settings={}):

        app = self.make_app(app_factory, settings_file, settings)

        request = app.make_blank_request('/')
        resource = Resource(app, request, 'shell')
        request.resource = resource
        request.resource_method = 'GET'
        app.mount_resource('shell', Resource, '/{action}')

        all_locals = {
            'app': app,
            'request': request,
            'resource': resource,
        }
        all_locals.update(locals_)

        tangled.commands.shell.implementation(config, shell_, all_locals)
