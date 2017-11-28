from tangled.scripts import ShellCommand
from tangled.web import Resource

from .mixins import AppMixin


class Command(ShellCommand, AppMixin):

    def __init__(self, parser, args):
        super().__init__(parser, args)
        AppMixin.__init__(self, parser, args)
        self.app = self.make_app()

    @classmethod
    def configure(cls, parser):
        AppMixin.configure(parser)
        super().configure(parser)

    def get_locals(self):
        request = self.app.make_blank_request('/')
        resource = Resource(self.app, request, 'shell', {'action': 'action'})
        request.resource = resource
        request.resource_method = 'GET'
        self.app.mount_resource('shell', Resource, '/{action}')
        return {
            'app': self.app,
            'request': request,
            'resource': resource,
        }
