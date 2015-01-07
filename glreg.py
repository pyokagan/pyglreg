#!/usr/bin/env python
r"""parse OpenGL registry files

This module provides functionality to parse and extract data from
OpenGL XML API Registry files. Types, enums and functions (commands) in the
registry can be enumerated. This module also provides functions to resolve
dependencies and filter APIs in the registry. This makes it useful for
generating OpenGL headers or loaders.

Load a `Registry` object from a file using `load`:

>>> registry = load(open('gl.xml'))

`Type` objects define the OpenGL types such as ``GLbyte``, ``GLint`` etc.

>>> registry.types
OrderedDict([(('stddef', None), Type(...)), ...
>>> registry.get_type('GLbyte')  # Get OpenGL's GLbyte typedef
Type('GLbyte', 'typedef signed char {name};')
>>> registry.get_type('GLbyte', 'gles2')  # Get OpenGLES2's GLbyte typedef
Type('GLbyte', 'typedef khronos_int8_t {name};', ...

`Enum` objects define OpenGL constants such as ``GL_POINTS``, ``GL_TRIANGLES``
etc.

>>> registry.enums
OrderedDict([('GL_CURRENT_BIT', Enum('GL_CURRENT_BIT', '0x00000001')), ...
>>> registry.enums['GL_POINTS']
Enum('GL_POINTS', '0x0000')

`Command` objects define OpenGL functions such as ``glClear``,
``glDrawArrays`` etc.

>>> registry.commands
OrderedDict([('glAccum', Command(...)), ('glAccumxOES', Command(...
>>> registry.commands['glDrawArrays']
Command('glDrawArrays', 'void {name}', [Param('mode', 'GLenum', ...

`Feature` objects are basically OpenGL version definitions. Each `Feature`
object lists the type, enum and command names that were introduced
in that version in internal `Require` objects.

>>> registry.features
OrderedDict([('GL_VERSION_1_0', Feature(...)), ('GL_VERSION_1_1', Feature(...
>>> registry.features['GL_VERSION_3_2']  # OpenGL version 3.2
Feature('GL_VERSION_3_2', 'gl', (3, 2), [Require([], ['GL_CONTEXT_CORE_PRO...
>>> feature = registry.features['GL_VERSION_3_2']
>>> feature.requires  # List of Require objects
[Require([], ['GL_CONTEXT_CORE_PROFILE_BIT', 'GL_CONTEXT_COMPATIBILITY...

On the other hand, `Remove` objects specify the types, enum and command names
that were removed in that version.

>>> feature.removes  # List of Remove objects
[Remove([], [], ['glNewList', 'glEndList', 'glCallList', 'glCallLists', ...

`Extension` objects are OpenGL extension definitions. Just like `Feature`
objects, each `Extension` object lists the type, enum and command names that
were defined in that extension in internal `Require` objects.

>>> registry.extensions
OrderedDict([('GL_3DFX_multisample', Extension(...)), ('GL_3DFX_tbuffer', ...

As we can see, Features and Extensions express dependencies and removals
of types, enums and commands in a registry through their `Require` and `Remove`
objects. These dependencies and removals can be resolved through the
`import_*` functions.

>>> dst = Registry()  # Destination registry
>>> import_feature(dst, registry, 'GL_VERSION_3_2')
>>> dst.features  # `dst` now only contains GL_VERSION_3_2 and its deps
OrderedDict([('GL_VERSION_3_2', Feature('GL_VERSION_3_2', 'gl', (3, 2), ...

Features can be filtered by api name and profile name, and Extensions can be
filtered by extension support strings. This allows you to extract, for example,
only the OpenGL core API or the OpenGL ES 2 API.

>>> dst = Registry()  # Destination registry
>>> import_registry(dst, registry, api='gl', profile='core', support='glcore')
>>> list(dst.features.keys())  # dst now only contains OpenGL Core features
['GL_VERSION_1_0', 'GL_VERSION_1_1', 'GL_VERSION_1_2', ...
>>> list(dst.extensions.keys())  # dst now only contains OpenGL Core extensions
['GL_ARB_ES2_compatibility', 'GL_ARB_ES3_1_compatibility', 'GL_ARB_ES3_comp...

Use the `get_apis`, `get_profiles` and `get_supports` member
functions of Registry objects to get all the api names, profile names and
extension support strings referenced in the registry respectively.

>>> sorted(registry.get_apis())
['gl', 'gles1', 'gles2']
>>> sorted(registry.get_profiles())
['common', 'compatibility', 'core']
>>> sorted(registry.get_supports())
['gl', 'glcore', 'gles1', 'gles2']

Finally, `group_apis` generates a new Registry for every feature and extension
in a registry, thus effectively grouping types, enums and commands with the
feature and extension or they were first defined in.

>>> group_apis(registry, api='gles2', support='gles2')
[Registry('GL_ES_VERSION_2_0', OrderedDict([(('khrplatform', None), Type...

This allows you to generate a simple OpenGL (ES) C header with a simple loop:

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

"""
from __future__ import print_function
import collections
import functools
import argparse
import re
import signal
import sys
import xml.etree.ElementTree
__author__ = 'Paul Tan <pyokagan@gmail.com>'
__version__ = '0.9.0a2'
__all__ = ['Type', 'Enum', 'Command', 'Param', 'Require', 'Remove', 'Feature',
           'Extension', 'Registry', 'load', 'loads', 'import_type',
           'import_command', 'import_enum', 'import_feature',
           'import_extension', 'import_registry', 'extension_name_sort_key',
           'group_apis']


def _repr(self, args, opt_args=()):
    args = list(args)
    args.extend(x for x in opt_args if x)
    return '{0}({1})'.format(self.__class__.__name__,
                             ', '.join(repr(x) for x in args))


class Type(object):
    def __init__(self, name, template, required_types=None, api=None,
                 comment=None):
        #: Type name
        self.name = str(name)
        #: Type definition template
        self.template = str(template)
        #: Set of strings specifying the names of types this type depends on
        self.required_types = set(required_types)
        #: API name which this Type is valid for
        self.api = api
        #: Optional comment
        self.comment = comment

    @property
    def text(self):
        """Formatted type definition

        Equivalent to ``self.template.format(name=self.name,
        apientry='APIENTRY')``
        """
        return self.template.format(name=self.name, apientry='APIENTRY')

    def __repr__(self):
        return _repr(self, (self.name, self.template),
                     (self.required_types, self.api, self.comment))


class Enum(object):
    def __init__(self, name, value, comment=None):
        #: Enum name
        self.name = str(name)
        #: Enum string value
        self.value = str(value)
        #: Optional comment
        self.comment = comment

    @property
    def text(self):
        """Formatted enum C definition

        Equivalent to ``'#define {0.name} {0.value}'.format(self)``
        """
        return '#define {0.name} {0.value}'.format(self)

    def __repr__(self):
        return _repr(self, (self.name, self.value), (self.comment,))


class Command(object):
    def __init__(self, name, proto_template, params, comment=None):
        #: Command name
        self.name = str(name)
        #: Command identifier template string
        self.proto_template = str(proto_template)
        #: List of command Params
        self.params = list(params)
        #: Optional comment
        self.comment = comment

    @property
    def required_types(self):
        """Set of names of types which the Command depends on.
        """
        required_types = set(x.type for x in self.params)
        required_types.discard(None)
        return required_types

    @property
    def proto_text(self):
        """Formatted Command identifier.

        Equivalent to ``self.proto_template.format(name=self.name)``.
        """
        return self.proto_template.format(name=self.name)

    @property
    def text(self):
        """Formatted Command declaration.

        This is the C declaration for the command.
        """
        params = ', '.join(x.text for x in self.params)
        return '{0} ({1});'.format(self.proto_text, params)

    def __repr__(self):
        return _repr(self, (self.name, self.proto_template, self.params),
                     (self.comment,))


class Param(object):
    def __init__(self, name, type, template):
        #: Param name
        self.name = name
        #: Name of type the param depends on, else None
        self.type = type
        #: Param definition template
        self.template = template

    @property
    def text(self):
        """Formatted param definition

        Equivalent to ``self.template.format(name=self.name, type=self.type)``.
        """
        return self.template.format(name=self.name, type=self.type)

    def __repr__(self):
        return _repr(self, (self.name, self.type, self.template))


class Require(object):
    """A requirement

    """

    def __init__(self, types, enums, commands, profile=None, api=None,
                 comment=None):
        #: List of type names which this Require requires
        self.types = types
        #: List of enum names which this Require requires
        self.enums = enums
        #: List of command names which this Require requires
        self.commands = commands
        #: Profile name which this Require is valid for
        self.profile = profile
        #: API name which this Require is valid for
        self.api = api  # NOTE: Only used in Extensions
        #: Optional comment
        self.comment = comment

    def as_symbols(self):
        """Set of symbols required by this Require

        :return: set of ``(symbol type, symbol name)`` tuples
        """
        out = set()
        for name in self.types:
            out.add(('type', name))
        for name in self.enums:
            out.add(('enum', name))
        for name in self.commands:
            out.add(('command', name))
        return out

    def __repr__(self):
        return _repr(self, (self.types, self.enums, self.commands),
                     (self.profile, self.api, self.comment))


class Remove(object):
    """Removal requirement

    """

    def __init__(self, types, enums, commands, profile=None, comment=None):
        #: List of type names of Types to remove
        self.types = types
        #: List of enum names of Enums to remove
        self.enums = enums
        #: List of command names of Commands to remove
        self.commands = commands
        #: Profile name which this Remove is valid for
        self.profile = profile
        #: Optional comment
        self.comment = comment

    def as_symbols(self):
        """Set of symbols required to be removed by this Remove

        :return: set of ``(symbol type, symbol name)`` tuples
        """
        out = set()
        for name in self.types:
            out.add(('type', name))
        for name in self.enums:
            out.add(('enum', name))
        for name in self.commands:
            out.add(('command', name))
        return out

    def __repr__(self):
        return _repr(self, (self.types, self.enums, self.commands),
                     (self.profile, self.comment))


class Feature(object):
    """Feature

    """

    def __init__(self, name, api, number, requires, removes, comment=None):
        #: Feature name
        self.name = name
        #: API name which this Feature is valid for
        self.api = api
        #: Feature version
        self.number = number
        #: List of Feature Require objects
        self.requires = list(requires or ())
        #: List of Feature Remove objects
        self.removes = list(removes or ())
        #: Optional comment
        self.comment = comment

    def get_apis(self):
        """Returns set of api names referenced in this Feature.

        :returns: set of api names
        """
        return set((self.api,) if self.api else ())

    def get_profiles(self):
        """Returns set of profile names referenced in this Feature

        :returns: set of profile names
        """
        out = set(x.profile for x in self.requires if x.profile)
        out.update(x.profile for x in self.removes if x.profile)
        return out

    def get_requires(self, profile=None):
        """Get filtered list of Require objects in this Feature

        :param str profile: Return Require objects with this profile or None
                            to return all Require objects.
        :return: list of Require objects
        """
        out = []
        for req in self.requires:
            # Filter Require by profile
            if ((req.profile and not profile) or
               (req.profile and profile and req.profile != profile)):
                continue
            out.append(req)
        return out

    def get_removes(self, profile=None):
        """Get filtered list of Remove objects in this Feature

        :param str profile: Return Remove objects with this profile or None
                            to return all Remove objects.
        :return: list of Remove objects
        """
        out = []
        for rem in self.removes:
            # Filter Remove by profile
            if ((rem.profile and not profile) or
               (rem.profile and profile and rem.profile != profile)):
                continue
            out.append(rem)
        return out

    def __repr__(self):
        return _repr(self, (self.name, self.api, self.number, self.requires,
                            self.removes), (self.comment,))


class Extension(object):
    """Extension

    """

    def __init__(self, name, supported, requires, comment=None):
        #: Extension name
        self.name = name
        #: Set of extension 'supported' strings
        self.supported = set(supported or ())
        #: List of `Require` objects
        self.requires = requires
        #: Optional comment
        self.comment = comment

    def get_apis(self):
        """Returns set of api names referenced in this Extension

        :return: set of api name strings
        """
        out = set()
        out.update(x.api for x in self.requires if x.api)
        return out

    def get_profiles(self):
        """Returns set of profile names referenced in this Extension

        :return: set of profile name strings
        """
        return set(x.profile for x in self.requires if x.profile)

    def get_supports(self):
        """Returns set of extension support strings referenced in Extension

        :return: set of extension support strings
        """
        return set(self.supported)

    def get_requires(self, api=None, profile=None):
        """Return filtered list of Require objects in this Extension

        :param str api: Return Require objects with this api name or None to
                        return all Require objects.
        :param str profile: Return Require objects with this profile or None
                            to return all Require objects.
        :return: list of Require objects
        """
        out = []
        for req in self.requires:
            # Filter Remove by API
            if (req.api and not api) or (req.api and api and req.api != api):
                continue
            # Filter Remove by profile
            if ((req.profile and not profile) or
               (req.profile and profile and req.profile != profile)):
                continue
            out.append(req)
        return out

    def __repr__(self):
        return _repr(self, (self.name, self.supported, self.requires),
                     (self.comment,))


class Registry:
    """API Registry

    """

    def __init__(self, name=None, types=None, enums=None, commands=None,
                 features=None, extensions=None):
        #: Optional API name (or None)
        self.name = name
        #: Mapping of ``(type name, type API)`` to `Type` objects
        self.types = collections.OrderedDict(types or ())
        #: Mapping of enum names to `Enum` objects
        self.enums = collections.OrderedDict(enums or ())
        #: Mapping of command names to `Command` objects
        self.commands = collections.OrderedDict(commands or ())
        #: Mapping of feature names to `Feature` objects
        self.features = collections.OrderedDict(features or ())
        #: Mapping of extension names to `Extension` objects
        self.extensions = collections.OrderedDict(extensions or ())

    @property
    def text(self):
        """Formatted API declarations.

        Equivalent to the concatenation of `text` attributes of
        types, enums and commands in this API.
        """
        out = []
        out.extend(x.text for x in self.types.values())
        out.extend(x.text for x in self.enums.values())
        out.extend('extern {0}'.format(x.text) for x in self.commands.values())
        return '\n'.join(out)

    def get_type(self, name, api=None):
        """Returns Type `name`, with preference for the Type of `api`.

        :param str name: Type name
        :param str api: api name to prefer, of None to prefer types with no
                        api name
        :return: Type object
        """
        k = (name, api)
        if k in self.types:
            return self.types[k]
        else:
            return self.types[(name, None)]

    def get_features(self, api=None):
        """Returns filtered list of features in this registry

        :param str api: Return only features with this api name, or None to
                        return all features.
        :return: list of Feature objects
        """
        return [x for x in self.features.values()
                if api and x.api == api or not api]

    def get_extensions(self, support=None):
        """Returns filtered list of extensions in this registry

        :param support: Return only extensions with this extension support
                        string, or None to return all extensions.
        :return: list of Extension objects
        """
        return [x for x in self.extensions.values() if support
                and support in x.supported or not support]

    def get_requires(self, api=None, profile=None, support=None):
        """Returns filtered list of Require objects in this registry

        :param str api: Return Require objects with this api name or None to
                        return all Require objects.
        :param str profile: Return Require objects with this profile or None
                            to return all Require objects.
        :param str support: Return Require objects with this extension support
                            string or None to return all Require objects.
        :return: list of Require objects
        """
        out = []
        for ft in self.get_features(api):
            out.extend(ft.get_requires(profile))
        for ext in self.extensions.values():
            # Filter extension support
            if support and support not in ext.supported:
                continue
            out.extend(ext.get_requires(api, profile))
        return out

    def get_removes(self, api=None, profile=None):
        """Returns filtered list of Remove objects in this registry

        :param str api: Return Remove objects with this api name or None to
                        return all Remove objects.
        :param str profile: Return Remove objects with this profile or None
                            to return all Remove objects.
        :return: list of Remove objects
        """
        out = []
        for ft in self.get_features(api):
            out.extend(ft.get_removes(profile))
        return out

    def get_apis(self):
        """Returns set of api names referenced in this Registry

        :return: set of api name strings
        """
        out = set(x.api for x in self.types.values() if x.api)
        for ft in self.features.values():
            out.update(ft.get_apis())
        for ext in self.extensions.values():
            out.update(ext.get_apis())
        return out

    def get_profiles(self):
        """Returns set of profile names referenced in this Registry

        :return: set of profile name strings
        """
        out = set()
        for ft in self.features.values():
            out.update(ft.get_profiles())
        for ext in self.extensions.values():
            out.update(ext.get_profiles())
        return out

    def get_supports(self):
        """Returns set of extension support strings referenced in this Registry

        :return: set of extension support strings
        """
        out = set()
        for ext in self.extensions.values():
            out.update(ext.get_supports())
        return out

    def __repr__(self):
        return _repr(self, (self.name,), (self.types, self.enums,
                     self.commands, self.features, self.extensions))


def _escape_tpl_str(x):
    def repl_f(match):
        if match.group(0) == '{':
            return '{{'
        else:
            return '}}'
    return re.sub('[{}]', repl_f, x)


def _load(root):
    """Load from an xml.etree.ElementTree"""
    types = _load_types(root)
    enums = _load_enums(root)
    commands = _load_commands(root)
    features = _load_features(root)
    extensions = _load_extensions(root)
    return Registry(None, types, enums, commands, features, extensions)


def _load_types(root):
    """Returns {name: Type}"""
    def text(t):
        if t.tag == 'name':
            return '{name}'
        elif t.tag == 'apientry':
            return '{apientry}'
        out = []
        if t.text:
            out.append(_escape_tpl_str(t.text))
        for x in t:
            out.append(text(x))
            if x.tail:
                out.append(_escape_tpl_str(x.tail))
        return ''.join(out)
    out_dict = collections.OrderedDict()
    for elem in root.findall('types/type'):
        name = elem.get('name') or elem.find('name').text
        template = text(elem)
        api = elem.get('api')
        if 'requires' in elem.attrib:
            required_types = set((elem.attrib['requires'],))
        else:
            required_types = set()
        comment = elem.get('comment')
        if api:
            k = (name, api)
        else:
            k = (name, None)
        out_dict[k] = Type(name, template, required_types, api, comment)
    return out_dict


def _load_enums(root):
    """Returns {name: Enum}"""
    out = collections.OrderedDict()
    for elem in root.findall('enums/enum'):
        name = elem.attrib['name']
        value = elem.attrib['value']
        comment = elem.get('comment')
        out[name] = Enum(name, value, comment)
    return out


def _load_param(elem):
    def text(t):
        if t.tag == 'name':
            return '{name}'
        elif t.tag == 'ptype':
            return '{type}'
        out = []
        if t.text:
            out.append(_escape_tpl_str(t.text))
        for x in t:
            out.append(text(x))
            if x.tail:
                out.append(_escape_tpl_str(x.tail))
        return ''.join(out)
    name = elem.find('name').text
    type_elem = elem.find('ptype')
    type = type_elem.text if type_elem is not None else None
    template = text(elem)
    return Param(name, type, template)


def _load_commands(root):
    """Returns {name: Command}"""
    def proto_text(t):
        if t.tag == 'name':
            return '{name}'
        out = []
        if t.text:
            out.append(_escape_tpl_str(t.text))
        for x in t:
            out.append(proto_text(x))
            if x.tail:
                out.append(_escape_tpl_str(x.tail))
        return ''.join(out)
    out = collections.OrderedDict()
    for elem in root.findall('commands/command'):
        name = elem.get('name') or elem.find('proto/name').text
        proto_template = proto_text(elem.find('proto'))
        params = [_load_param(x) for x in elem.findall('param')]
        comment = elem.get('comment')
        out[name] = Command(name, proto_template, params, comment)
    return out


def _load_require(elem):
    types = [x.attrib['name'] for x in elem.findall('type')]
    enums = [x.attrib['name'] for x in elem.findall('enum')]
    commands = [x.attrib['name'] for x in elem.findall('command')]
    profile = elem.get('profile')
    api = elem.get('api')
    comment = elem.get('comment')
    return Require(types, enums, commands, profile, api, comment)


def _load_remove(elem):
    types = [x.attrib['name'] for x in elem.findall('type')]
    enums = [x.attrib['name'] for x in elem.findall('enum')]
    commands = [x.attrib['name'] for x in elem.findall('command')]
    profile = elem.get('profile')
    comment = elem.get('comment')
    return Remove(types, enums, commands, profile, comment)


def _load_features(root):
    """Returns {name: Feature}"""
    out = collections.OrderedDict()
    for elem in root.findall('feature'):
        name = elem.attrib['name']
        api = elem.attrib['api']
        number = tuple([int(x) for x in elem.attrib['number'].split('.')])
        requires = [_load_require(x) for x in elem.findall('require')]
        removes = [_load_remove(x) for x in elem.findall('remove')]
        comment = elem.get('comment')
        out[name] = Feature(name, api, number, requires, removes, comment)
    return out


def _load_extensions(root):
    """Returns {name: Extension}"""
    out = collections.OrderedDict()
    for elem in root.findall('extensions/extension'):
        name = elem.attrib['name']
        supported = set(elem.attrib['supported'].split('|'))
        requires = [_load_require(x) for x in elem.findall('require')]
        comment = elem.get('comment')
        out[name] = Extension(name, supported, requires, comment)
    return out


def load(f):
    """Loads Registry from file

    :param f: File to load
    :type f: File-like object
    :return: Registry
    """
    return _load(xml.etree.ElementTree.parse(f))


def loads(s):
    """Load registry from string

    :param s: Registry XML contents
    :type s: str or bytes
    :return: Registry
    """
    return _load(xml.etree.ElementTree.fromstring(s))


def _default_filter_symbol(t, name):
    assert type(t) is str
    assert type(name) is str
    return True


def _default_filter_require(require):
    assert type(require) is Require
    return True


def import_type(dest, src, name, api=None, filter_symbol=None):
    """Import Type `name` and its dependencies from Registry `src`
    to Registry `dest`.

    :param Registry dest: Destination Registry
    :param Registry src: Source Registry
    :param str name: Name of type to import
    :param str api: Prefer to import Types with api Name `api`, or None to
                    import Types with no api name.
    :param filter_symbol: Optional filter callable
    :type filter_symbol: Callable with signature
                         ``(symbol_type:str, symbol_name:str) -> bool``
    """
    if not filter_symbol:
        filter_symbol = _default_filter_symbol
    type = src.get_type(name, api)
    for x in type.required_types:
        if not filter_symbol('type', x):
            continue
        import_type(dest, src, x, api, filter_symbol)
    dest.types[(type.name, type.api)] = type


def import_command(dest, src, name, api=None, filter_symbol=None):
    """Import Command `name` and its dependencies from API `src`
    to API `dest`

    :param Registry dest: Destination Registry
    :param Registry src: Source Registry
    :param str name: Name of Command to import
    :param str api: Prefer to import Types with api name `api`, or None to
                    import Types with no api name
    :param filter_symbol: Optional filter callable
    :type filter_symbol: Callable with signature
                         ``(symbol_type:str, symbol_name:str) -> bool``
    """
    if not filter_symbol:
        filter_symbol = _default_filter_symbol
    cmd = src.commands[name]
    for x in cmd.required_types:
        if not filter_symbol('type', x):
            continue
        import_type(dest, src, x, api, filter_symbol)
    dest.commands[name] = cmd


def import_enum(dest, src, name):
    """Import Enum `name` from API `src` to API `dest`.

    :param Registry dest: Destination Registry
    :param Registry src: Source Registry
    :param str name: Name of Enum to import
    """
    dest.enums[name] = src.enums[name]


def import_feature(dest, src, name, api=None, profile=None,
                   filter_symbol=None):
    """Imports Feature `name`, and all its dependencies, from
    Registry `src` to API `dest`.

    :param Registry dest: Destination Registry
    :param Registry src: Source Registry
    :param str name: Name of Feature to import
    :param str api: Prefer to import dependencies with api name `api`,
                    or None to import dependencies with no API name.
    :param str profile: Import dependencies with profile name
                        `profile`, or None to import all dependencies.
    :param filter_symbol: Optional symbol filter callable
    :type filter_symbol: Callable with signature
                         ``(symbol_type:str, symbol_name:str) -> bool``
    """
    if filter_symbol is None:
        filter_symbol = _default_filter_symbol
    ft = src.features[name] if isinstance(name, str) else name
    # Gather symbols to remove from Feature
    remove_symbols = set()
    for x in src.get_removes(api, profile):
        remove_symbols.update(x.as_symbols())

    def my_filter_symbol(t, name):
        return False if (t, name) in remove_symbols else filter_symbol(t, name)

    for req in ft.get_requires(profile):
        for x in req.types:
            if not my_filter_symbol('type', x):
                continue
            import_type(dest, src, x, api, filter_symbol)
        for x in req.enums:
            if not my_filter_symbol('enum', x):
                continue
            import_enum(dest, src, x)
        for x in req.commands:
            if not my_filter_symbol('command', x):
                continue
            import_command(dest, src, x, api, filter_symbol)
    dest.features[name] = ft


def import_extension(dest, src, name, api=None, profile=None,
                     filter_symbol=None):
    """Imports Extension `name`, and all its dependencies.

    :param Registry dest: Destination Registry
    :param Registry src: Source Registry
    :param str name: Name of Extension to import
    :param str api: Prefer to import types with API name `api`,
                or None to prefer Types with no API name.
    :type api: str
    :param filter_symbol: Optional symbol filter callable
    :type filter_symbol: Callable with signature
                         ``(symbol_type:str, symbol_name:str) -> bool``
    """
    if filter_symbol is None:
        filter_symbol = _default_filter_symbol
    ext = src.extensions[name] if isinstance(name, str) else name
    for req in ext.get_requires(api, profile):
        for x in req.types:
            if not filter_symbol('type', x):
                continue
            import_type(dest, src, x, api, filter_symbol)
        for x in req.enums:
            if not filter_symbol('enum', x):
                continue
            import_enum(dest, src, x)
        for x in req.commands:
            if not filter_symbol('command', x):
                continue
            import_command(dest, src, x, api, filter_symbol)
    dest.extensions[name] = ext


def import_registry(dest, src, api=None, profile=None, support=None,
                    filter_symbol=None):
    """Imports all features and extensions and all their dependencies.

    :param Registry dest: Destination API
    :param Registry src: Source Registry
    :param str api: Only import Features with API name `api`, or None
                    to import all features.
    :param str profile: Only import Features with profile name `profile`,
                        or None to import all features.
    :param str support: Only import Extensions with this extension support
                        string, or None to import all extensions.
    :param filter_symbol: Optional symbol filter callable
    :type filter_symbol: Callable with signature
                         ``(symbol_type:str, symbol_name:str) -> bool``
    """
    if filter_symbol is None:
        filter_symbol = _default_filter_symbol
    for x in src.get_features(api):
        import_feature(dest, src, x.name, api, profile, filter_symbol)
    for x in src.get_extensions(support):
        import_extension(dest, src, x.name, api, profile, filter_symbol)


def extension_name_sort_key(name):
    """Returns the sorting key for an extension name.

    The sorting key can be used to sort a list of extension names
    into the order that is used in the Khronos C OpenGL headers.
    """
    category = name.split('_', 2)[1]
    return (0, name) if category in ('ARB', 'KHR', 'OES') else (1, name)


def group_apis(reg, features=None, extensions=None, api=None, profile=None,
               support=None):
    """Groups Types, Enums, Commands with their respective Features, Extensions

    Similar to :py:func:`import_registry`, but generates a new Registry object
    for every feature or extension.

    :param Registry reg: Input registry
    :param features: Feature names to import, or None to import all.
    :type features: Iterable of strs
    :param extensions: Extension names to import, or None to import all.
    :type extensions: Iterable of strs
    :param str profile: Import features which belong in `profile`, or None
                        to import all.
    :param str api: Import features which belong in `api`, or None to
                    import all.
    :param str support: Import extensions which belong in this extension
                        support string, or None to import all.
    :returns: list of :py:class:`Registry` objects
    """
    features = (reg.get_features(api) if features is None
                else [reg.features[x] for x in features])
    extensions = (reg.get_extensions(support) if extensions is None
                  else [reg.extensions[x] for x in extensions])
    output_symbols = set()

    def filter_symbol(type, name):
        k = (type, name)
        if k in output_symbols:
            return False
        else:
            output_symbols.add(k)
            return True

    out_apis = []
    for x in features:
        out = Registry(x.name)
        import_feature(out, reg, x, api, profile, filter_symbol)
        out_apis.append(out)
    for x in extensions:
        out = Registry(x.name)
        import_extension(out, reg, x, api, profile, filter_symbol)
        out_apis.append(out)
    return out_apis


def main(args=None, prog=None):
    """Generates a C header file"""
    args = args if args is not None else sys.argv[1:]
    prog = prog if prog is not None else sys.argv[0]
    # Prevent broken pipe exception from being raised.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    stdin = sys.stdin.buffer if hasattr(sys.stdin, 'buffer') else sys.stdin
    p = argparse.ArgumentParser(prog=prog)
    p.add_argument('-o', '--output', type=argparse.FileType('w'),
                   help='Output path', default=sys.stdout)
    p.add_argument('--api', help='Match API', default=None)
    p.add_argument('--profile', help='Match profile', default=None)
    p.add_argument('--support', default=None,
                   help='Match extension support string')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--list-apis', action='store_true', dest='list_apis',
                   help='List apis in registry', default=False)
    g.add_argument('--list-profiles', action='store_true', default=False,
                   dest='list_profiles', help='List profiles in registry')
    g.add_argument('--list-supports', action='store_true',
                   dest='list_supports', default=False,
                   help='List extension support strings')
    p.add_argument('registry', type=argparse.FileType('rb'), nargs='?',
                   default=stdin, help='Registry path')
    args = p.parse_args(args)
    o = args.output
    try:
        registry = load(args.registry)
        if args.list_apis:
            for x in sorted(registry.get_apis()):
                print(x, file=o)
            return 0
        elif args.list_profiles:
            for x in sorted(registry.get_profiles()):
                print(x, file=o)
            return 0
        elif args.list_supports:
            for x in sorted(registry.get_supports()):
                print(x, file=o)
            return 0
        apis = group_apis(registry, None, None, args.api, args.profile,
                          args.support)
        for api in apis:
            print('#ifndef', api.name, file=o)
            print('#define', api.name, file=o)
            print(api.text, file=o)
            print('#endif', file=o)
            print('', file=o)
    except:
        e = sys.exc_info()[1]
        print(prog, ': error: ', e, sep='', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:], sys.argv[0]))
