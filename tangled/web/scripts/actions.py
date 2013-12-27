import argparse
import re

from tangled.web.settings import parse_settings, parse_settings_file


class SettingsFileAction(argparse.Action):

    def __call__(self, parser, namespace, value, option_string=None):
        settings = parse_settings_file(value)
        setattr(namespace, self.dest, settings)


class SettingsAction(argparse.Action):

    pattern = re.compile(r'^(?P<k>.+)=(?P<v>.+)$')

    def __call__(self, parser, namespace, values, option_string=None):
        settings = {}
        for value in values:
            match = self.pattern.search(value)
            if not match:
                raise ValueError(value)
            k, v = match.group('k'), match.group('v')
            settings[k] = v
        settings = parse_settings(settings)
        setattr(namespace, self.dest, settings)
