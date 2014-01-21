Contributing
++++++++++++

Issues
======

Bugs and other issues can be reported on `GitHub`_.

Patches
=======

To contribute patches, go to the TangledWeb project on `GitHub`_, fork a
package, and send a pull request. All new code must be 100% covered by tests
and be `PEP8`_ compliant.

Creating an Extension Package
=============================

To create your own extension package, you can use the ``tangled.contrib``
namespace. If you install the ``tangled.contrib`` package, you will be able to
create a contrib package easily using the ``tangled scaffold`` command::

    tangled scaffold contrib tangled.contrib.{name}

.. _GitHub: https://github.com/TangledWeb
.. _PEP8: http://www.python.org/dev/peps/pep-0008/
