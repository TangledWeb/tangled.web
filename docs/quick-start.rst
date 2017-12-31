Quick Start
+++++++++++

This is a short guide that will show you the basics of creating a Web
application based on ``tangled.web``.

Install Python 3.4+
===================

First, install Python 3.4 or newer.

You can download Python 3 `from here <https://www.python.org/downloads/>`_. If
you're using Mac OS, `Homebrew <http://brew.sh/>`_ is an easy way to install
Python::

    brew install python3

.. note:: Python 2.x is *not* supported, and there are no plans to support it.

Virtualenv
==========

Next, set up an isolated virtual environment. Since we're using Python 3, this
is built in. The command for creating a virtual env looks like this::

    python3 -m venv helloworld.venv

Change into the ``helloworld.venv`` directory and download the following file
there:

https://raw.github.com/pypa/pip/master/contrib/get-pip.py

Then run the following command::

    python get-pip.py

Install Dependencies
====================

The ``tangled.web`` package needs to be installed so that the
``tangled scaffold`` command and ``basic`` scaffold are available::

    pip install tangled.web

If you want to use the latest code, you can do this instead::

    pip install -e https://github.com/TangledWeb/tangled#egg=tangled
    pip install -e https://github.com/TangledWeb/tangled.web#egg=tangled.web

Create a Basic Tangled Web App
==============================

Now that the virtual environment is set up and the Tangled dependencies have
been installed, a project can be created. Run the following commands in the
``helloworld.venv`` directory::

    tangled scaffold basic helloworld
    pip install -e helloworld

Serve it Up
===========

Now that everything's installed, it's time to run the app::

    tangled serve -f helloworld/development.ini

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
