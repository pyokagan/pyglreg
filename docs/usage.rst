User Guide
===========
.. currentmodule:: glreg

Loading a Registry
-------------------
Begin by importing the glreg module:

>>> import glreg

Use :func:`glreg.load` to load a `OpenGL XML API Registry file`_.
Assuming our file is named :file:`gl.xml` in the current directory:

.. _OpenGL XML API Registry file:
    https://cvs.khronos.org/svn/repos/ogl/trunk/doc/registry/public/api/gl.xml

>>> registry = glreg.load(open('gl.xml'))

:func:`glreg.load` returns a :class:`glreg.Registry` object.

Types
------
:class:`glreg.Type` objects define the OpenGL types such as
``GLbyte``, ``GLint`` etc.

:attr:`Registry.types` is a :class:`collections.OrderedDict` object
mapping ``(type name, type api)`` tuples to :class:`Type` objects:

>>> registry.types
OrderedDict([(('stddef', None), Type(...)), ...

Use :meth:`Registry.get_type` to look up :class:`Type` objects by
their name as it will take into account both Types with an API name specified
and Types with no API name specified.

>>> registry.get_type('GLbyte')  # Get OpenGL's GLbyte typedef
Type('GLbyte', 'typedef signed char {name};')
>>> registry.get_type('GLbyte', 'gles2')  # Get OpenGLES2's GLbyte typedef
Type('GLbyte', 'typedef khronos_int8_t {name};', ...
>>> registry.get_type('GLbyte') is registry.get_type('GLbyte', 'gles2')
False
>>> registry.get_type('GLsync', 'gles2') 
Type('GLsync', 'typedef struct __GLsync ...
>>> registry.get_type('GLsync')
Type('GLsync', 'typedef struct __GLsync ...
>>> registry.get_type('GLsync') is registry.get_type('GLsync', 'gles2')
True

:attr:`Type.template` is the template string of the type in Python's
Format String Syntax (:pep:`3101`). It has a `name` replacement field where the
type's identifier needs to be substituted in. It is usually
:attr:`Type.name` or some similar variant.

>>> t = registry.get_type('GLbyte')
>>> t.template
'typedef signed char {name};'
>>> t.template.format(name=t.name)
'typedef signed char GLbyte;'

The :attr:`Type.text` convenience attribute does this common substitution.

>>> t.text
'typedef signed char GLbyte;'

Note that :class:`Type` objects can depend on other types. Their names
are listed in :attr:`Type.required_types`

>>> t = registry.get_type('GLbyte', 'gles2')
>>> t.required_types
{'khrplatform'}

Enums
------
:class:`glreg.Enum` objects define the OpenGL constants
such as ``GL_POINTS``, ``GL_TRIANGLES`` etc.

:attr:`Registry.enums` is a :class:`collections.OrderedDict` object
mapping enum names to :class:`Enum` objects:

>>> registry.enums
OrderedDict([('GL_CURRENT_BIT', Enum('GL_CURRENT_BIT', '0x00000001')), ...
>>> registry.enums['GL_POINTS']
Enum('GL_POINTS', '0x0000')

Commands
---------
:class:`glreg.Command` objects define OpenGL functions
such as ``glClear`` and ``glDrawArrays``.

:attr:`Registry.commands` is a :class:`collections.OrderedDict` object
mapping command names to :class:`Command` objects:

>>> registry.commands
OrderedDict([('glAccum', Command(...)), ('glAccumxOES', Command(...
>>> registry.commands['glDrawArrays']
Command('glDrawArrays', 'void {name}', [Param('mode', 'GLenum', ...

:class:`Command` objects contain their `prototype template` and a list
of its parameters as :class:`Param` objects:

>>> cmd = registry.commands['glDrawArrays']
>>> cmd.proto_template  # The command's prototype template
'void {name}'
>>> cmd.proto_text  # Convenience attribute for command's prototype
'void glDrawArrays'
>>> cmd.params  # The command's parameters
[Param('mode', 'GLenum', '{type} {name}'), Param('first', 'GLint', ...


Features
---------
:class:`glreg.Feature` objects are basically OpenGL version definitions.

:attr:`Registry.features` is a :class:`collections.OrderedDict` object
mapping feature names to :class:`Feature` objects.

>>> registry.features
OrderedDict([('GL_VERSION_1_0', Feature(...)), ('GL_VERSION_1_1', Feature(...

Each :class:`Feature` object lists the type, enum and command names
that were introduced in that version in internal :class:`Require` objects.

>>> registry.features['GL_VERSION_3_2']  # OpenGL version 3.2
Feature('GL_VERSION_3_2', 'gl', (3, 2), [Require([], ['GL_CONTEXT_CORE_PRO...
>>> feature = registry.features['GL_VERSION_3_2']
>>> feature.requires  # List of Require objects
[Require([], ['GL_CONTEXT_CORE_PROFILE_BIT', 'GL_CONTEXT_COMPATIBILITY...

On the other hand, :class:`Remove` objects specify the types, enum and
command names that were removed in that version.

>>> feature.removes  # List of Remove objects
[Remove([], [], ['glNewList', 'glEndList', 'glCallList', 'glCallLists', ...

Extensions
------------
:class:`glreg.Extension` objects are OpenGL extension definitions.
Just like :class:`Feature` objects, each :class:`Extension` object
list the type, enum and command names that were defined in that extension
in internal :class:`Require` objects.

>>> registry.extensions
OrderedDict([('GL_3DFX_multisample', Extension(...)), ('GL_3DFX_tbuffer', ...

Handling dependencies and removals
------------------------------------
As seen above, :class:`Feature` objects and :class:`Extension` objects
express dependency and removals of types, enums and commands in a registry
through their :class:`Require` and :class:`Remove` objects. These
dependencies and removals can be resolved using the Registry Importing
functions.

:func:`glreg.import_type` imports a :class:`Type` and its dependencies
from one :class:`Registry` object to another.

>>> dst_reg = glreg.Registry()
>>> glreg.import_type(dst_reg, registry, 'GLbyte')
>>> dst_reg.types
OrderedDict([(('GLbyte', None), Type('GLbyte', 'typedef signed char ...
>>> dst_reg = glreg.Registry()
>>> glreg.import_type(dst_reg, registry, 'GLbyte', api='gles2')
>>> dst_reg.types
OrderedDict([(('khrplatform', None), Type('khrplatform', ...

:func:`glreg.import_enum` imports a :class:`Enum` from one
:class:`Registry` object to another.
Note that :class:`Enum` objects have no dependencies.

>>> dst_reg = glreg.Registry()
>>> glreg.import_enum(dst_reg, registry, 'GL_POINTS')
>>> dst_reg.enums
OrderedDict([('GL_POINTS', Enum('GL_POINTS', '0x0000'))])

:func:`glreg.import_command` imports a :class:`Command` and its
dependencies from one :class:`Registry` to another.

>>> dst_reg = glreg.Registry()
>>> glreg.import_command(dst_reg, registry, 'glBufferData')
>>> dst_reg.commands
OrderedDict([('glBufferData', Command('glBufferData', 'vo...

:func:`glreg.import_feature` imports a :class:`Feature` and its
dependencies from one :class:`Registry` to another. Removals which are
active in the source Registry will be taken into account -- all their
specified types, enums and commands will not be imported.

>>> dst_reg = Registry()
>>> glreg.import_feature(dst, registry, 'GL_VERSION_3_2')
>>> dst_reg.features  # `dst_reg` now only contains GL_VERSION_3_2 and its deps
OrderedDict([('GL_VERSION_3_2', Feature('GL_VERSION_3_2', 'gl', (3, 2), ...

:func:`glreg.import_extension` imports a :class:`Extension` and its
dependencies from one :class:`Registry` to another.

>>> dst_reg = Registry()
>>> glreg.import_extension(dst_reg, registry, 'GL_ARB_ES2_compatibility')
>>> dst_reg.extensions
OrderedDict([('GL_ARB_ES2_compatibility', Extension('GL_ARB_ES2_c...

Filtering Features and Extensions
----------------------------------
When calling :func:`glreg.import_feature` without any of its filter
arguments, close inspection of the destination registry will reveal that
both OpenGL and OpenGL ES commands are mixed together, and that the
OpenGL types have overridden the OpenGL ES types. This is undesirable for
applications which only target OpenGL and OpenGL ES.

We can ensure that only OpenGL or OpenGL ES types, enums and commands
are imported into the destination registry using filters.

:class:`Feature` objects can be filtered by `api name` and
`profile name`. :class:`Extension` objects can be filtered by
`extension support strings`.

>>> dst = Registry()  # Destination registry
>>> import_registry(dst, registry, api='gl', profile='core', support='glcore')
>>> list(dst.features.keys())  # dst now only contains OpenGL Core features
['GL_VERSION_1_0', 'GL_VERSION_1_1', 'GL_VERSION_1_2', ...
>>> list(dst.extensions.keys())  # dst now only contains OpenGL Core extensions
['GL_ARB_ES2_compatibility', 'GL_ARB_ES3_1_compatibility', 'GL_ARB_ES3_comp...

:meth:`Registry.get_apis`, :meth:`Registry.get_profiles` and
:meth:`Registry.get_supports` will return all the
api names, profile names and extension support strings referenced in the
registry respectively.

>>> sorted(registry.get_apis())
['gl', 'gles1', 'gles2']
>>> sorted(registry.get_profiles())
['common', 'compatibility', 'core']
>>> sorted(registry.get_supports())
['gl', 'glcore', 'gles1', 'gles2']

Grouping Types, Enums and Commands by their Feature or Extension
-----------------------------------------------------------------
OpenGL C header files typically group types, enums and commands by
the feature or extension where they were first introduced. This can
be accomplished using :func:`glreg.group_apis`.

:func:`glreg.group_apis` generates a new :class:`Registry` object
for every feature and extension in a registry while importing their
types, enums and commands. This effectively groups types, enums and
commands with the feature or extension where they were first defined.

>>> group_apis(registry, api='gles2', support='gles2')
[Registry('GL_ES_VERSION_2_0', OrderedDict([(('khrplatform', None), Type...

A simple OpenGL (ES) C header can thus be generated with the following loop:

>>> for api in group_apis(registry, api='gles2', support='gles2'):
...     print('#ifndef ' + api.name)
...     print('#define ' + api.name)
...     print(api.text)
...     print('#endif')
#ifndef GL_ES_VERSION_2_0
#define GL_ES_VERSION_2_0
#include <KHR/khrplatform.h>
typedef khronos_int8_t GLbyte;
...

Command-line interface
-----------------------
.. program:: glreg

When run as a script from the command line, glreg provides a simple
command line interface for generating C header files from a registry.

Example usage:

.. code-block:: shell

    $ python -mglreg --list-apis gl.xml
    gl
    gles1
    gles2
    $ python -mglreg --list-profiles gl.xml
    common
    compatibility
    core
    $ python -mglreg --list-supports gl.xml
    gl
    glcore
    gles1
    gles2
    $ python -mglreg --api gl --profile core --support glcore gl.xml
    #ifndef GL_VERSION_1_0
    #define GL_VERSION_1_0
    typedef void GLvoid;
    typedef unsigned int GLenum;
    typedef int GLint;
    typedef int GLsizei;
    typedef double GLdouble;
    typedef unsigned int GLbitfield;
    typedef float GLfloat;
    typedef unsigned char GLboolean;
    typedef unsigned int GLuint;
    extern void glBlendFunc(GLenum sfactor, GLenum dfactor);
    extern void glClear(GLbitfield mask);...

The command-line arguments are as follows:

.. option:: registry

   Registry path. If this argument is not provided, :program:`glreg` will
   read the registry from standard input.

.. option:: -o PATH, --output PATH

   Write output to `PATH`.

.. option:: --api API

   Output only features with API name `API`.

.. option:: --profile PROFILE

   Output only features with profile name `PROFILE`.

.. option:: --support SUPPORT

   Output only extensions with extension support string `SUPPORT`.

.. option:: --list-apis

   List api names in registry.

.. option:: --list-profiles

   List profile names in registry.

.. option:: --list-supports

   List extension support strings in registry

Limitations
-------------
* ``<remove>`` tags in ``<extension>`` tags, despite being defined in
  the schema, is not supported because they do not make sense.
* ``<group>`` tags are not supported yet.
