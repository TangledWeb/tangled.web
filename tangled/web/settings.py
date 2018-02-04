from functools import partial

from tangled.converters import as_meth_args
from tangled.settings import parse_settings, parse_settings_file, check_required

from .abcs import AAppSettings


def get_conversion_map(**overrides):
    # Map of setting `key` => `converter`; `converter` can be any callable
    # that takes a single argument and returns a value. `converter` can also
    # be a string naming a builtin or converter from `tangled.converters`.
    conversion_map = {
        'debug': 'bool',
        'debug.pdb': 'bool',
        'factory': 'object',
        'tangled.app.cors.enabled': 'bool',
        'tangled.app.cors.permissive': 'bool',
        'tangled.app.csrf.enabled': 'bool',
        'tangled.app.error_resource': 'object',
        'tangled.app.exc_log_message_factory': 'object',
        'tangled.app.handlers': 'list',
        'tangled.app.includes': 'list',
        'tangled.app.defer_created': 'bool',
        'tangled.app.on_created': 'list_of_objects',
        'tangled.app.representation.json.encoder': 'object',
        'tangled.app.representation.json.encoder.default': 'object',
        'tangled.app.request_factory': 'object',
        'tangled.app.response_factory': 'object',
        'tangled.app.resources':
            as_meth_args('tangled.web:Application.mount_resource'),
        'tangled.app.load_config': 'tuple',
        'tangled.app.set_accept_from_ext': 'bool',
        'tangled.app.static_directories':
            as_meth_args('tangled.web:Application.mount_static_directory'),
        'tangled.app.tunnel_over_post': 'tuple',
    }
    conversion_map.update(overrides)
    return conversion_map


def make_app_settings(settings, conversion_map={}, defaults={}, required=(), section='app',
                      **extra_settings):
    """Create a properly initialized application settings dict.

    In simple cases, you don't need to call this directly--you can pass
    a settings file name or dict to :class:`tangled.web.app.Application`
    and this will be called for you.

    If you need to do custom parsing (e.g., if your app has custom
    settings), you can call this function with a conversion map,
    defaults, &c. It's a wrapper around :func:`.parse_settings` that
    adds a bit of extra functionality:

        - A file name can be passed instead of a settings dict, in
          which case the settings will be extracted from the specified
          ``section`` of that file.
        - Core tangled.web defaults are *always* added because
          :class:`tangled.web.app.Application` assumes they are always
          set.
        - Additional defaults can be passed; these will override the
          corresponding tangled.web defaults.
        - Extra settings can be passed as keyword args; they will
          override all other settings, and they will be parsed along
          with other settings.
        - Required settings are checked for after all the settings are
          merged.

    In really special cases you can create an instance of
    :class:`.AAppSettings` and then construct your settings dict
    manually.

    """
    conversion_map = get_conversion_map(**conversion_map)
    parse = partial(parse_settings, conversion_map=conversion_map)
    parse_file = partial(parse_settings_file, conversion_map=conversion_map)

    all_settings = parse_file('tangled.web:defaults.ini', meta_settings=False)
    all_settings.update(parse(defaults))
    if isinstance(settings, str):
        all_settings.update(parse_file(settings, section=section))
    else:
        all_settings.update(parse(settings))
    all_settings.update(parse(extra_settings))

    check_required(all_settings, required)
    return AppSettings(all_settings)


AppSettings = type('AppSettings', (dict,), {})
AAppSettings.register(AppSettings)
