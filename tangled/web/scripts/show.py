from tangled.abcs import ACommand

from .mixins import AppMixin


CHOICES = ['settings', 'handlers', 'resources']


def choice(value):
    if value not in CHOICES:
        raise ValueError(value)
    return value


class Command(ACommand, AppMixin):

    def __init__(self, parser, args):
        super().__init__(parser, args)
        AppMixin.__init__(self, parser, args)
        self.app = self.make_app()

    @classmethod
    def configure(cls, parser):
        AppMixin.configure(parser)
        parser.add_argument('what', nargs='*', type=choice, default=CHOICES)

    def run(self):
        for what in self.args.what:
            print('[{}]'.format(what))
            getattr(self, 'show_{}'.format(what))()
            print()

    def show_handlers(self):
        for handler in self.app._handlers:
            print('{0.__module__}:{0.__name__}'.format(handler.callable_))

    def show_settings(self):
        for k in sorted(self.app.settings):
            v = self.app.settings[k]
            print('{} = {}'.format(k, v))

    def show_resources(self):
        print('not yet implemented')
