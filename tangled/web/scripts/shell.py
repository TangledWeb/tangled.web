import code
import sys

from tangled.abcs import ACommand
from tangled.util import load_object
from tangled.web.resource import Resource

from .mixins import AppMixin


def strip_lower(val):
    return val.strip().lower()


def local_type(val):
    k, v = val.split('=')
    v = load_object(v)
    return k, v


class Command(ACommand, AppMixin):

    # In order of preference
    shells = ['bpython', 'ipython', 'python']

    def __init__(self, parser, args):
        super().__init__(parser, args)
        AppMixin.__init__(self, parser, args)
        self.app = self.make_app()

    @classmethod
    def configure(cls, parser):
        AppMixin.configure(parser)
        parser.add_argument(
            '--shell', type=strip_lower, choices=cls.shells, default=None)
        parser.add_argument(
            'locals', nargs='*', type=local_type,
            help='Pass additional shell locals using '
                 'name=package.module:object syntax')

    def run(self):
        request = self.app.make_blank_request('/')
        resource = Resource(self.app, request, 'shell', {'action': 'action'})
        self.app.mount_resource('shell', Resource, '/{action}')

        shell_locals = {
            'app': self.app,
            'request': request,
            'resource': resource,
        }
        if self.args.locals:
            shell_locals.update(self.args.locals)

        banner = ['Shell locals:']
        banner += [
            'app: {}'.format(self.app),
            'request: {0.method} {0.url}'.format(request),
        ]
        banner = '\n'.join(banner)

        def try_shells(shells):
            for shell in shells:
                success = getattr(self, shell)(shell_locals, banner)
                if success:
                    return shell

        if self.args.shell:
            if not try_shells([self.args.shell]):
                alt_shells = self.shells[:]
                alt_shells.remove(self.args.shell)
                self.print_error(
                    '{} shell not available; trying others ({})'
                    .format(self.args.shell, ', '.join(alt_shells)))
                try_shells(alt_shells)
        else:
            try_shells(self.shells)

    def bpython(self, shell_locals, banner):
        try:
            import bpython
            from bpython import embed
        except ImportError:
            return False
        banner = 'bpython {}\n\n{}'.format(bpython.__version__, banner)
        embed(locals_=shell_locals, banner=banner)
        return True

    def ipython(self, shell_locals, banner):
        try:
            from IPython.terminal.embed import InteractiveShellEmbed
        except ImportError:
            return False
        InteractiveShellEmbed(user_ns=shell_locals, banner2=banner)()
        return True

    def python(self, shell_locals, banner):
        banner = 'python {}\n\n{}'.format(sys.version, banner)
        code.interact(banner=banner, local=shell_locals)
        return True
