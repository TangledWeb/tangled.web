Request Handlers
++++++++++++++++

Adding request handlers
=======================

Handlers are callables with the signature ``(app, request, next_handler)``.

.. automethod:: tangled.web.app.Application.add_handler

System handler chain
====================

`Adding request handlers`_

.. automodule:: tangled.web.handlers
    :members:
    :member-order: bysource
