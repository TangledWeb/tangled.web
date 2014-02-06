Tangled.Web
+++++++++++

.. image:: https://travis-ci.org/TangledWeb/tangled.web.png?branch=master
   :target: https://travis-ci.org/TangledWeb/tangled.web

Tangled.Web is a somewhat opinionated, resource oriented Web framework. It
might be considered a "micro" framework because it simply provides a way to map
HTTP requests to resources and has no opinions regarding databases, templating,
etc.

Unlike many other frameworks, there are no "views" or "controllers" here, only
resources. Resources respond to HTTP requests and return representations based
on the client's preference (indicated via Accept headers).

`Documentation (in progress) <http://tangledframework.org/docs/tangled.web/>`_

Python 3
========

Tangled.Web runs *only* on Python 3.3+. Part of the reason for this is simply
that I didn't feel like dealing with straddling 2|3. I also wanted to use some
features that aren't available in earlier versions (e.g., built-in namespace
packages). Finally, I've been itching to really learn all the new Python 3
goodness, and a Python 3 only project seemed like a good way to do that (it
has been so far).

I'm also of the opinion that Python 3 has *almost* arrived. Most of the
libraries I've been using for the past several years (SQLAlchemy, Mako, WebOb,
etc) have already been ported.
