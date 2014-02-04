import functools

from tangled.converters import as_args
from tangled.settings import parse_settings, parse_settings_file


# Map of setting `key` => `converter`; `converter` can be any callable
# that takes a single argument and returns a value. `converter` can also
# be a string naming a builtin or converter from `tangled.converters`.
CONVERSION_MAP = {
    'debug': 'bool',
    'debug.pdb': 'bool',
    'tangled.app.csrf.enabled': 'bool',
    'tangled.app.error_resource': 'object',
    'tangled.app.handlers': 'list',
    'tangled.app.includes': 'list',
    'tangled.app.on_created': 'list_of_objects',
    'tangled.app.representation.json.encoder': 'object',
    'tangled.app.representation.json.encoder.default': 'object',
    'tangled.app.request_factory': 'object',
    'tangled.app.response_factory': 'object',
    'tangled.app.resources': as_args(None, None, None, None, 'bool'),
    'tangled.app.scan': 'tuple',
    'tangled.app.static_directories': as_args(None, None, 'bool', None),
    'tangled.app.tunnel_over_post': 'tuple',
}

parse_settings = functools.partial(
    parse_settings, conversion_map=CONVERSION_MAP)

parse_settings_file = functools.partial(
    parse_settings_file, conversion_map=CONVERSION_MAP)
