Resources
+++++++++

- `Creating resources`_
- `Configuring resources`_
- `Mounting resources`_

Creating resources
==================

Usually, you will want to create your resources as subclasses of
:class:`tangled.web.resource.resource.Resource`.

.. autoclass:: tangled.web.resource.resource.Resource
    :members:

Configuring resources
=====================

The :class:`tangled.web.resource.config.config` decorator is used to configure
resource classes and methods.

.. automodule:: tangled.web.resource.config
    :members: config

Mounting Resources
==================

.. automethod:: tangled.web.app.Application.mount_resource
