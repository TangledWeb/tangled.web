Request
+++++++

Adding request methods
======================

.. automethod:: tangled.web.app.Application.add_request_attribute

Request factories
=================

These two methods make it easy to create properly configured requests. In
particular, they set the request's ``app`` attribute, and they create
request instances with the attributes added via
:meth:`tangled.web.app.Application.add_request_attribute`.

.. automethod:: tangled.web.app.Application.make_request
.. automethod:: tangled.web.app.Application.make_blank_request
