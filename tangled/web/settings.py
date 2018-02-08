from tangled.settings import parse_settings_file, check_required

from .abcs import AAppSettings


def make_app_settings(settings, section='app', defaults={}, required=(), extra={}):
    """Create a properly initialized application settings dict.

    This is a wrapper around :func:`.parse_settings_file` that adds
    a bit of extra functionality:

        - A file name can be passed instead of a settings dict, in
          which case the settings will be extracted from the specified
          ``section`` of that file.
        - Core tangled.web defaults are *always* added because
          :class:`tangled.web.app.Application` assumes they are always
          set.
        - Additional defaults can be passed; these will override the
          corresponding tangled.web defaults.
        - Extra settings can be passed; they will override all other
          settings.
        - Required settings are checked for after all the settings are
          merged.

    In most cases, you don't need to call this directly--you can pass
    a settings file name or dict to :class:`tangled.web.app.Application`
    and this will be called for you.

    """
    all_settings = parse_settings_file('tangled.web:defaults.ini', meta_settings=False)
    all_settings.update(defaults)
    if isinstance(settings, str):
        all_settings.update(parse_settings_file(settings, section=section))
    else:
        all_settings.update(settings)
    all_settings.update(extra)
    check_required(all_settings, required)
    return AppSettings(all_settings)


AppSettings = type('AppSettings', (dict,), {})
AAppSettings.register(AppSettings)
