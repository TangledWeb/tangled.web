import argparse
import re

from tangled.web import make_app_settings


class SettingsFileAction(argparse.Action):

    def __call__(self, parser, namespace, value, option_string=None):
        settings = make_app_settings(value)
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
        settings = make_app_settings(settings)
        setattr(namespace, self.dest, settings)
