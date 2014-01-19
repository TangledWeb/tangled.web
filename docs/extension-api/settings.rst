Settings
++++++++

Parsing settings
================

.. method:: tangled.web.app.Application.parse_settings

    This is a ``staticmethod`` wrapper around
    :func:`tangled.web.settings.parse_settings`, which is in turn
    a wrapper around :func:`tangled.settings.parse_settings` with
    ``conversion_map`` set to
    :const:`tangled.web.settings.CONVERSION_MAP`.

Parsing settings from a file
============================

.. method:: tangled.web.app.Application.parse_settings_file

    This is a ``staticmethod`` wrapper around
    :func:`tangled.web.settings.parse_settings_file`, which is in turn
    a wrapper around :func:`tangled.settings.parse_settings_file` with
    ``conversion_map`` set to
    :const:`tangled.web.settings.CONVERSION_MAP`.
