Quick Start
+++++++++++

This is a short guide that will show you the basics of creating a Web
application based on ``tangled.web``.

Install Python 3.3+
===================

First, install Python 3.3. Older versions of Python 3 *will not* work. Mainly,
this is because of the use of built-in namespace package support that was
added in Python 3.3.

You can download Python 3.3
`from here <http://www.python.org/download/releases/3.3.3/>`_. If you're using
Mac OS, `Homebrew <http://brew.sh/>`_ is an easy way to install Python::

    brew install python3

.. note:: Python 2.x is *not* supported, and there are no plans to support it.

Virtual Env
===========

Next, set up an isolated virtual environment. Since we're using Python 3, this
is built in. The command for creating a virtual env looks like this::

    python3 -m venv helloworld.venv

Change into the ``helloworld.venv`` directory and download the following file
there:

https://raw.github.com/pypa/pip/master/contrib/get-pip.py

Then run the following command::

    ./bin/python get-pip.py

Install Dependencies
====================

A couple of Tangled dependencies need to be installed so that the
``tangled scaffold`` command and ``basic`` scaffold are available::

    ./bin/pip install tangled.web==VERSION

Replace `VERSION` with the version you want to install. The current version
is |version|.

If you want to use the latest code, you can do this instead (requires git to be
installed)::

    ./bin/pip install -e git+git://github.com/TangledWeb/tangled#egg=tangled
    ./bin/pip install -e git+git://github.com/TangledWeb/tangled.web#egg=tangled.web

Create a Basic Tangled Web App
==============================

Now that the virtual environment is set up and the Tangled dependencies have
been installed, a project can be created. Run the following commands in the
``helloworld.venv`` directory::

    ./bin/tangled scaffold basic helloworld
    ./bin/pip install -e helloworld

Serve it Up
===========

Now that everything's installed, it's time to run the app::

    ./bin/tangled serve -f helloworld/development.ini

Now you can visit http://localhost:6666/ and http://localhost:6666/name.

Next Steps
==========

Take a look at the app configuration in ``helloworld/helloworld/__init__.py``
and the ``Hello`` resource in ``helloworld/helloworld/resources.py``.

The :doc:`app-api/index` documentation currently has the most comprehensive
info on creating and configuring Tangled Web apps.

.. note:: This is all still very much a work in progress. Please feel free to
          make suggestions or report issues
          `on GitHub <https://github.com/TangledWeb/tangled.web/issues>`_.
