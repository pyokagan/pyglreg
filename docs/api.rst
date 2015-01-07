API Reference
==============

.. py:module:: glreg

:py:mod:`glreg` provides functionality to parse and extract data from
OpenGL XML API Registry files. Types, enums and functions (commands) in the
registry can be enumerated. This module also provides functions to resolve
dependencies and filter APIs in the registry. This makes it useful for
generating OpenGL headers or loaders.

Classes
--------

.. autoclass:: Registry
    :members:

.. autoclass:: Type
    :members:

.. autoclass:: Enum
    :members:

.. autoclass:: Command
    :members:

.. autoclass:: Param
    :members:

.. autoclass:: Feature
    :members:

.. autoclass:: Extension
    :members:

.. autoclass:: Require
    :members:

.. autoclass:: Remove
    :members:


Registry loading functions
----------------------------

.. autofunction:: load

.. autofunction:: loads


Registry importing functions
-----------------------------

.. autofunction:: import_type

.. autofunction:: import_enum

.. autofunction:: import_command

.. autofunction:: import_feature

.. autofunction:: import_extension

.. autofunction:: import_registry


API grouping functions
-----------------------

.. autofunction:: group_apis

