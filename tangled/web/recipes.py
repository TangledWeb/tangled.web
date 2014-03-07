"""Buildout recipes."""
import os
import zc.buildout
from zc.recipe.egg.egg import Eggs


TEMPLATE = """\
import sys

SYS_PATHS = [{sys_paths}]

for path in reversed(SYS_PATHS):
    if path not in sys.path:
        sys.path[0:0] = [path]

from tangled.util import load_object

FACTORY = load_object('{factory}')
SETTINGS_FILE = '{settings_file}'
PARSE_SETTINGS = {parse_settings}
EXTRA_SETTINGS = {{{extra_settings}}}
{initialization}
application = FACTORY(
    SETTINGS_FILE,
    parse_settings=PARSE_SETTINGS,
    **EXTRA_SETTINGS
)
\
"""


class WSGIApplication(object):

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

        if 'eggs' not in options:
            raise zc.buildout.UserError(
                'You must specify one or more eggs using the `eggs` option')

        if 'app-factory' not in options:
            options['app-factory'] = 'tangled.web:Application'

        if 'settings-file' not in options:
            raise zc.buildout.UserError(
                'You must specify a settings file using the `settings-file` '
                'option')

    def install(self):
        egg = Eggs(self.buildout, self.options['recipe'], self.options)
        requirements, working_set = egg.working_set()
        sys_paths = [dist.location for dist in working_set]
        if sys_paths:
            sys_paths = ''.join("    '{}',\n".format(p) for p in sys_paths)
            sys_paths = '\n{}'.format(sys_paths)
        else:
            sys_paths = ''

        extra_settings = {}
        for k, v in self.options.items():
            include = (
                (k not in self.buildout['buildout']) and
                (k not in (
                    '_d', '_e', 'recipe', 'eggs', 'app-factory',
                    'settings-file', 'initialization'))
            )
            if include:
                extra_settings[k] = v
        if extra_settings:
            extra_settings = ''.join(
                "    '{}': '{}',\n"
                .format(k, v) for (k, v) in extra_settings.items())
            extra_settings = '\n{}'.format(extra_settings)
        else:
            extra_settings = ''

        initialization = self.options.get('initialization', '')
        if initialization:
            initialization = '\n{}\n'.format(initialization)

        contents = TEMPLATE.format(
            sys_paths=sys_paths,
            factory=self.options['app-factory'],
            settings_file=self.options['settings-file'],
            parse_settings=self.options.get('parse-settings', True),
            extra_settings=extra_settings,
            initialization=initialization,
        )

        output_file = self.options.get('output-file')
        if output_file is None:
            output_file = os.path.join(
                self.buildout['buildout']['directory'], 'application.wsgi')

        with open(output_file, 'w') as fp:
            fp.write(contents)

        self.options.created(output_file)
        return self.options.created()

    def update(self):
        self.install()
