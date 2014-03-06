Main Documentation
++++++++++++++++++

Displaying Errors
=================

By default, errors will be displayed using the plain error templates
provided by WebOb. To customize the display of errors, an error resource
needs to be created. The simplest error resource looks like this:

.. code-block:: python

    from tangled.web import Resource, config


    class Error(Resource):

        @config('text/html', template='/error.html')
        def GET(self):
            return {}


``error.html`` would contain contents like this:

.. code-block:: xml

    <%inherit file="/layout.html"/>

    <h1>Error</h1>

    <div class="error">
      The request failed with status code ${request.status_code}
    </div>


To activate the error resource, point the ``tangled.app.error_resource``
setting at it:

.. code-block:: ini

    [app]
    tangled.app.error_resource = my.pkg.resources.error:Error
