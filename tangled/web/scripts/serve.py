import datetime
import glob
import os
import subprocess
import sys
import threading
import time
import traceback
from wsgiref.simple_server import make_server

from tangled.abcs import ACommand
from tangled.util import fully_qualified_name

from .mixins import AppMixin


class Command(ACommand, AppMixin):

    def __init__(self, parser, args):
        super().__init__(parser, args)
        AppMixin.__init__(self, parser, args)

    @classmethod
    def configure(cls, parser):
        AppMixin.configure(parser)
        parser.add_argument('-H', '--host', default='0.0.0.0')
        parser.add_argument('-p', '--port', type=int, default=6666)
        parser.add_argument(
            '--no-reload', dest='reload', action='store_false', default=True,
            help='Disable reloading when files change')
        parser.add_argument(
            '--reload-interval', type=int, default=1,
            help='How often (in seconds) to check for changed files')

    def run(self):
        if self.args.reload and not os.environ.get('MONITOR'):
            return self.run_with_monitor()

        print('[{}]'.format(datetime.datetime.now()))
        factory_name = fully_qualified_name(self.args.app_factory)
        print('Creating app from {} factory'.format(factory_name))
        app = self.make_app()

        server = None
        try:
            message = 'Starting server on http://{0.host}:{0.port}/'
            server = make_server(self.args.host, self.args.port, app)
            if self.args.reload:
                message += ' with file monitor'
                reload_interval = self.args.reload_interval
                monitor_thread = MonitorThread(server, reload_interval)
                monitor_thread.start()
            message += '...'
            print(message.format(self.args))
            server.serve_forever()  # Blocks until server.shutdown()
        except KeyboardInterrupt:
            print('\rAborted')
        except:
            traceback.print_exc()
            self.exit('\nCould not start server', 2)
        finally:
            if server is not None:
                server.shutdown()
                server.server_close()

    def run_with_monitor(self):
        argv = sys.argv.copy()
        os.environ['MONITOR'] = '1'
        while True:
            try:
                exit_code = subprocess.call(argv)
                if exit_code:
                    if exit_code == 1:  # Error in app startup code
                        msg = '\rAttempting restart in {} seconds...'
                        seconds = 5
                        while seconds:
                            self.print_error(msg.format(seconds), end='')
                            seconds -= 1
                            time.sleep(1)
                        print('\n')
                    else:
                        self.exit(status=exit_code)
            except KeyboardInterrupt:
                break


class MonitorThread(threading.Thread):

    """Monitors all modules on sys.path and config files."""

    def __init__(self, server, interval):
        self.server = server
        self.interval = interval
        self.files = {f: os.stat(f).st_mtime for f in self.files_to_monitor}
        super().__init__()

    def run(self):
        while self.server:
            changed = list(self.changed_files)
            if changed:
                print('Changed files detected:')
                for file_name in changed:
                    print('    {}'.format(file_name))
                self.server.shutdown()
                break
            time.sleep(self.interval)

    @property
    def files_to_monitor(self):
        # Modules
        modules = sys.modules.values()
        yield from (m.__file__ for m in modules if getattr(m, '__file__', ''))
        # Config files
        for root, dirs, files in os.walk(os.getcwd()):
            if root.startswith('.'):
                continue
            yield from glob.iglob(os.path.join(root, '*.ini'))

    @property
    def changed_files(self):
        for file_name in self.files:
            if os.path.exists(file_name):
                old_mtime = self.files[file_name]
                new_mtime = os.stat(file_name).st_mtime
                if old_mtime < new_mtime:
                    yield file_name
            else:
                # File was renamed or removed?
                yield file_name
