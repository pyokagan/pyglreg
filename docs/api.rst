API Reference
==============
.. module:: glreg

:mod:`glreg` provides functionality to parse and extract data from
OpenGL XML API Registry files. Types, enums and functions (commands) in the
registry can be enumerated. This module also provides functions to resolve
dependencies and filter APIs in the registry. This makes it useful for
generating OpenGL headers or loaders.

Classes
--------
.. autoclass:: Registry
   :members: get_type, get_features, get_extensions, get_requires,
             get_removes, get_apis, get_profiles, get_supports

   .. attribute:: name

      Optional Registry name (or None)

   .. attribute:: types

      :class:`collections.OrderedDict` mapping of ``(type name, type API)``
      to :class:`Type` objects.

   .. attribute:: enums

      :class:`collections.OrderedDict` mapping of enum names to :class:`Enum`
      objects.

   .. attribute:: commands

      :class:`collections.OrderedDict` mapping of command names to
      :class:`Command` objects.

   .. attribute:: features

      :class:`collections.OrderedDict` mapping of feature names to
      :class:`Feature` objects.

   .. attribute:: extensions

      :class:`collections.OrderedDict` mapping of extension names to
      :class:`Extension` objects.

   .. attribute:: text

      (readonly) Formatted API declarations. Equivalent to the concatenation of
      `text` attributes of all types, enums and commands in this
      registry.

.. autoclass:: Type

   .. attribute:: name

      Type name

   .. attribute:: template

       Type definition template with the following arguments:

       * `name`: name of the type (usually :attr:`Type.name`)
       * `apientry`: calling convention macro (usually the string ``APIENTRY``,
         which is a C macro defined by the system platform headers)

   .. attribute:: required_types

      :class:`set` of :class:`str` specifying the names of types this type
      depends on.

   .. attribute:: api

      API name which this Type is valid for

   .. attribute:: comment

      Optional comment, or None

   .. attribute:: text
    
      (readonly) Formatted type definition. Equivalent to
      ``self.template.format(name=self.name, apientry='APIENTRY')``

.. autoclass:: Enum

   .. attribute:: name

      Enum name

   .. attribute:: value

      Enum string value

   .. attribute:: comment

      Optional comment, or None

   .. attribute:: text

      (readonly) Formatted enum C definition. Equivalent to
      ``'#define {0.name} {0.value}'.format(self)``

.. autoclass:: Command

   .. attribute:: name
   
      Command name

   .. attribute:: type

      Command return type, or None

   .. attribute:: proto_template

      Command identifier template string with the following arguments:

      * `name`: Command name (usually :attr:`Command.name`)
      * `type`: Command return type (usually :attr:`Command.type`). This
        argument is only used when this command has a return type.

   .. attribute:: params

      :class:`list` of command :class:`Params`

   .. attribute:: comment

      Optional comment, or None

   .. attribute:: required_types

      (readonly) :class:`set` of names of types which this Command depends on.

   .. attribute:: proto_text

      (readonly) Formatted Command identifier. Equivalent to
      ``self.proto_template.format(type=self.type, name=self.name)``

   .. attribute:: text
   
      (readonly) Formatted Command C declaration.

.. autoclass:: Param

   .. attribute:: name

      Param name

   .. attribute:: type

      Optional name of Param type, or None

   .. attribute:: template

      Param definition template with the following arguments:

      * `name`: Param name (usually :attr:`Param.name`)
      * `type`: Param type (usually :attr:`Param.type`). This argument is
        only used when this Param has a type.

   .. attribute:: text

      Formatted Param definition. Equivalent to
      ``self.template.format(name=self.name, type=self.type)``

.. autoclass:: Feature
   :members: get_apis, get_profiles, get_requires, get_removes

   .. attribute:: name

      Feature name

   .. attribute:: api

      API name which this Feature is valid for

   .. attribute:: number

      Feature number as ``(major, minor)`` tuple.

   .. attribute:: requires

      :class:`list` of Feature :class:`Require` objects.

   .. attribute:: removes

      :class:`list` of Feature :class:`Remove` objects.

   .. attribute:: comment

      Optional comment, or None.

.. autoclass:: Extension
   :members: get_apis, get_profiles, get_supports, get_requires

   .. attribute:: name

      Extension name

   .. attribute:: supported

      :class:`set` of extension 'supported' strings

   .. attribute:: requires

      :class:`list` of :class:`Require` objects

   .. attribute:: comment

      Optional comment, or None.

.. autoclass:: Require
   :members: as_symbols

   .. attribute:: types

      :class:`list` of type names which this Require requires.

   .. attribute:: enums

      :class:`list` of enum names which this Require requires.

   .. attribute:: commands

      :class:`list` of command names which this Require requires.

   .. attribute:: profile

      Profile name which this Require is valid for

   .. attribute:: api

      API name which this Require is valid for

   .. attribute:: comment

      Optional comment, or None.

.. autoclass:: Remove
   :members: as_symbols

   .. attribute:: types

      List of type names of Types to remove.

   .. attribute:: enums

      List of enum names of Enums to remove.

   .. attribute:: commands

      List of command names of Commands to remove.

   .. attribute:: profile

      Profile name which this Remove is valid for.

   .. attribute:: comment

      Optional comment, or None.

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

