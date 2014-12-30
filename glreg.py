#!/usr/bin/env python
r"""parse OpenGL registry files

This module parses OpenGL API XML registry files and extracts data which can be
used to generate OpenGL headers and loading libraries.
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
__version__ = '0.9.0'
__all__ = ['Type', 'Enum', 'Command', 'Param', 'Require', 'Remove', 'Feature',
           'Extension', 'API', 'Registry', 'load', 'loads', 'get_type',
           'import_type', 'import_command', 'import_enum', 'import_feature',
           'import_extension', 'import_registry', 'get_requires',
           'get_removes', 'get_profiles', 'get_apis',
           'get_extension_support_strings', 'extension_name_sort_key',
           'generate_api']


class Type(object):
    name = None  # Type name
    template = None  # Type template string
    text = None  # Type string
    required_types = None  # Set of Type names which this Type depends on
    api = None  # API for which the Type is valid


class Enum(object):
    name = None  # Enum string name
    value = None  # Enum string value


class Command(object):
    name = None  # Command name
    proto_template = None  # Command prototype template string
    proto_text = None  # Command prototype text string
    params = None  # List of Params
    required_types = None  # Set of Type names which this command depends on


class Param(object):
    name = None  # Parameter name
    template = None  # Parameter template string
    text = None  # Parameter text string


class Require(object):
    types = None  # Set of type names required
    enums = None  # Set of enum names required
    commands = None  # Set of command names required
    api = None  # API which this requirement is valid for
    profile = None  # Profile which this requirement is valid for


class Remove(object):
    types = None  # Set of type names to remove
    enums = None  # Set of enum names to remove
    commands = None  # Set of command names to remove
    profile = None  # Profile which this removal is valid for


class Feature(object):
    name = None  # Feature name
    api = None  # Feature API name
    number = None  # Feature number as a (major, minor) tuple
    requires = None  # List of requirements
    removes = None  # List of removals


class Extension(object):
    name = None  # Extension name
    supported = None  # Set of 'supported' strings
    requires = None  # List of requirements


class API(object):
    def __init__(self):
        self.name = None  # Optional name
        self.types = collections.OrderedDict()
        self.enums = {}
        self.commands = {}


class Registry(API):
    def __init__(self):
        super(Registry, self).__init__()
        self.features = {}
        self.extensions = {}


def _escape_tpl_str(x):
    def repl_f(match):
        if match.group(0) == '{':
            return '{{'
        else:
            return '}}'
    return re.sub('[{}]', repl_f, x)


def _load(tree):
    """Load from an xml.etree.ElementTree"""
    out = Registry()
    root = tree.getroot()
    out.types = _load_types(root)
    out.enums = _load_enums(root)
    out.commands = _load_commands(root)
    out.features = _load_features(root)
    out.extensions = _load_extensions(root)
    return out


def _load_types(root):
    """Returns {name: Type}"""
    def text(t, template):
        if t.tag == 'name' and template:
            return '{name}'
        elif t.tag == 'apientry' and template:
            return '{apientry}'
        out = []
        if t.text:
            out.append(_escape_tpl_str(t.text) if template else t.text)
        for x in t:
            out.append(text(x, template))
            if x.tail:
                out.append(_escape_tpl_str(x.tail) if template else x.tail)
        return ''.join(out)
    out_dict = collections.OrderedDict()
    for elem in root.findall('types/type'):
        out = Type()
        out.name = elem.get('name') or elem.find('name').text
        out.template = text(elem, True)
        out.text = text(elem, False)
        if 'requires' in elem.attrib:
            out.required_types = set((elem.attrib['requires'],))
        else:
            out.required_types = set()
        out.api = elem.get('api')
        if out.api:
            k = (out.name, out.api)
        else:
            k = (out.name, None)
        out_dict[k] = out
    return out_dict


def _load_enums(root):
    """Returns {name: Enum}"""
    out = {}
    for elem in root.findall('enums/enum'):
        enum = Enum()
        enum.name = elem.attrib['name']
        enum.value = elem.attrib['value']
        out[enum.name] = enum
    return out


def _load_param(elem):
    def text(t, template):
        if t.tag == 'name' and template:
            return '{name}'
        out = []
        if t.text:
            out.append(_escape_tpl_str(t.text) if template else t.text)
        for x in t:
            out.append(text(x, template))
            if x.tail:
                out.append(_escape_tpl_str(x.tail) if template else x.tail)
        return ''.join(out)
    out = Param()
    out.name = elem.find('name').text
    out.template = text(elem, True)
    out.text = text(elem, False)
    return out


def _load_commands(root):
    """Returns {name: Command}"""
    def proto_text(t, template):
        if t.tag == 'name' and template:
            return '{name}'
        out = []
        if t.text:
            out.append(_escape_tpl_str(t.text) if template else t.text)
        for x in t:
            out.append(proto_text(x, template))
            if x.tail:
                out.append(_escape_tpl_str(x.tail) if template else x.tail)
        return ''.join(out)
    out = {}
    for elem in root.findall('commands/command'):
        cmd = Command()
        cmd.name = elem.get('name') or elem.find('proto/name').text
        cmd.proto_template = proto_text(elem.find('proto'), True)
        cmd.proto_text = proto_text(elem.find('proto'), False)
        cmd.params = [_load_param(x) for x in elem.findall('param')]
        cmd.required_types = set()
        for elem2 in elem.findall('.//ptype'):
            cmd.required_types.add(elem2.text)
        out[cmd.name] = cmd
    return out


def _load_require(elem):
    out = Require()
    out.profile = elem.get('profile')
    out.api = elem.get('api')
    out.types = set([x.attrib['name'] for x in elem.findall('type')])
    out.enums = set([x.attrib['name'] for x in elem.findall('enum')])
    out.commands = set([x.attrib['name'] for x in elem.findall('command')])
    return out


def _load_remove(elem):
    out = Remove()
    out.profile = elem.get('profile')
    out.types = set([x.attrib['name'] for x in elem.findall('type')])
    out.enums = set([x.attrib['name'] for x in elem.findall('enum')])
    out.commands = set([x.attrib['name'] for x in elem.findall('command')])
    return out


def _load_features(root):
    """Returns {name: Feature}"""
    out = {}
    for elem in root.findall('feature'):
        ft = Feature()
        ft.name = elem.attrib['name']
        ft.api = elem.attrib['api']
        ft.number = tuple([int(x) for x in elem.attrib['number'].split('.')])
        ft.types = set()
        ft.requires = [_load_require(x) for x in elem.findall('require')]
        ft.removes = [_load_remove(x) for x in elem.findall('remove')]
        out[ft.name] = ft
    return out


def _load_extensions(root):
    """Returns {name: Extension}"""
    out = {}
    for elem in root.findall('extensions/extension'):
        ext = Extension()
        ext.name = elem.attrib['name']
        ext.supported = set(elem.attrib['supported'].split('|'))
        ext.requires = [_load_require(x) for x in elem.findall('require')]
        out[ext.name] = ext
    return out


def load(f):
    """Loads Registry from file"""
    return _load(xml.etree.ElementTree.parse(f))


def loads(s):
    """Load registry from string"""
    return _load(xml.etree.ElementTree.fromstring(s))


def _default_filter_symbol(t, name):
    assert type(t) is str
    assert type(name) is str
    return True


def _default_filter_require(require):
    assert type(require) is Require
    return True


def get_type(src, name, api=None):
    """Returns Type `name` from API `src`, with preference for the
    Type that requires API `api`."""
    k = (name, api)
    if k in src.types:
        return src.types[k]
    else:
        return src.types[(name, None)]


def import_type(dest, src, name, api=None, filter_symbol=None):
    """Import Type `name` and its dependencies from API `src`
    to API `dest`"""
    if not filter_symbol:
        filter_symbol = _default_filter_symbol
    type = get_type(src, name, api)
    for x in type.required_types:
        if not filter_symbol('type', x):
            continue
        import_type(dest, src, x, api, filter_symbol)
    dest.types[name] = type


def import_command(dest, src, name, api=None, filter_symbol=None):
    """Import Command `name` and its dependencies from API `src`
    to API `dest`"""
    if not filter_symbol:
        filter_symbol = _default_filter_symbol
    cmd = src.commands[name]
    for x in cmd.required_types:
        if not filter_symbol('type', x):
            continue
        import_type(dest, src, x, api, filter_symbol)
    dest.commands[name] = cmd


def import_enum(dest, src, name):
    """Import Enum `name` from API `src` to API `dest`."""
    dest.enums[name] = src.enums[name]


def import_feature(dest, src, name, api=None, filter_symbol=None,
                   filter_require=None):
    """Imports Feature `name`, and all its dependencies, from
    Registry `src` to API `dest`."""
    if filter_symbol is None:
        filter_symbol = _default_filter_symbol
    if filter_require is None:
        filter_require = _default_filter_require
    ft = src.features[name] if isinstance(name, str) else name
    for req in ft.requires:
        if not filter_require(req):
            continue
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
    if hasattr(dest, 'features'):
        dest.features[name] = ft


def import_extension(dest, src, name, api=None, filter_symbol=None,
                     filter_require=None):
    """Imports Extension `name`, and all its dependencies, from
    Registry `src` to API `dest`."""
    if filter_symbol is None:
        filter_symbol = _default_filter_symbol
    if filter_require is None:
        filter_require = _default_filter_require
    ext = src.extensions[name] if isinstance(name, str) else name
    for req in ext.requires:
        if not filter_require(req):
            continue
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
    if hasattr(dest, 'extensions'):
        dest.extensions[name] = ext


def import_registry(dest, src, api=None, extension_support=None,
                    filter_symbol=None, filter_require=None):
    """Imports all features and extensions, and all their dependencies,
    from Registry `src` to API `dest`."""
    if api and not extension_support:
        extension_support = api
    if filter_symbol is None:
        filter_symbol = _default_filter_symbol
    if filter_require is None:
        filter_require = _default_filter_require
    for k, v in src.features.items():
        if v.api and api and v.api != api:
            continue
        import_feature(dest, src, k, api, filter_symbol, filter_require)
    for k, v in src.extensions.items():
        if extension_support and extension_support not in v.supported:
            continue
        import_extension(dest, src, k, api, filter_symbol, filter_require)


def get_requires(reg):
    """Returns the set of Require objects in the Registry `reg`."""
    out = set()
    for ft in reg.features.values():
        out.update(ft.requires)
    for ext in reg.extensions.values():
        out.update(ext.requires)
    return out


def get_removes(reg):
    """Returns the set of Remove objects in the Registry `reg`."""
    out = set()
    for ft in reg.features.values():
        out.update(ft.removes)
    return out


def get_profiles(reg):
    """Returns the set of profiles defined in the Registry `reg`."""
    out = set()
    for req in get_requires(reg):
        if req.profile:
            out.add(req.profile)
    for rem in get_removes(reg):
        if rem.profile:
            out.add(rem.profile)
    return out


def get_apis(reg):
    """Returns the set of api names defined in the Registry `reg`."""
    out = set()
    for ft in reg.features.values():
        out.add(ft.api)
    return out


def get_extension_support_strings(reg):
    """Returns the set of extension support strings defined in the
    Registry `reg`.
    """
    out = set()
    for ext in reg.extensions.values():
        out.update(ext.supported)
    return out


def extension_name_sort_key(name):
    """Returns the sorting key for an extension name.

    The sorting key can be used to sort a list of extension names
    into the order that is used in the Khronos C OpenGL headers.
    """
    category = name.split('_', 2)[1]
    return (0, name) if category in ('ARB', 'KHR', 'OES') else (1, name)


def generate_api(reg, features=None, extensions=None, profile=None,
                 api=None, extension_support=None):
    """Algorithm for generating API from Registry `reg`. Returns a list of
    APIs.

    `features` is an iterable of feature names, or None to match all features
    in registry `reg`.
    `extensions` is an iterable of extension names, or None to match all
    extensions in registry `reg`.
    `profile` is the profile to match, or None to match all profiles.
    `api` is the API name to match, or None to match all apis.
    `extension_support` is the extension support string to match, or None to
    match all extension support strings.
    """

    if features is None:
        features = reg.features.keys()
    features = sorted(features)

    if extensions is None:
        extensions = reg.extensions.keys()
    extensions = sorted(extensions, key=extension_name_sort_key)

    # Collect all remove symbols in registry
    remove_symbols = set()
    for x in features:
        ft = reg.features[x]
        for rem in ft.removes:
            if ((rem.profile and not profile) or
               (rem.profile and profile and rem.profile != profile)):
                continue
            for name in rem.types:
                remove_symbols.add(('type', name))
            for name in rem.enums:
                remove_symbols.add(('enum', name))
            for name in rem.commands:
                remove_symbols.add(('command', name))

    # Build filter_symbol and filter_require
    output_symbols = set()

    def filter_symbol(type, name):
        k = (type, name)
        if k in output_symbols or k in remove_symbols:
            return False
        else:
            output_symbols.add(k)
            return True

    def filter_require(req):
        t1 = (req.profile == profile) if req.profile and profile else True
        t2 = req.api == api if req.api and api else True
        return t1 and t2

    # Build APIs
    out_apis = []

    for x in features:
        ft = reg.features[x]
        if api and ft.api != api:
            continue
        out = API()
        import_feature(out, reg, x, api, filter_symbol, filter_require)
        out.name = x
        out_apis.append(out)

    for x in extensions:
        out = API()
        ext = reg.extensions[x]
        if extension_support and extension_support not in ext.supported:
            continue
        import_extension(out, reg, x, api, filter_symbol, filter_require)
        out.name = x
        out_apis.append(out)

    return out_apis


def test_load_types():
    contents = r'''<?xml version="1.0" encoding="UTF-8" ?>
    <registry><types>
    <type name="khrplatform">#include &lt;KHR/khrplatform.h&gt;</type>
    <type>typedef signed char <name>GLbyte</name>;</type>
    <type api="gles2"
    requires="khrplatform">typedef khronos_int8_t <name>GLbyte</name>;</type>
    </types></registry>
    '''
    root = xml.etree.ElementTree.fromstring(contents)
    d = _load_types(root)
    assert isinstance(d, dict)
    assert len(d) == 3
    x = d[('khrplatform', None)]
    assert isinstance(x, Type)
    assert x.name == 'khrplatform'
    assert x.template == '#include <KHR/khrplatform.h>'
    assert x.api is None
    assert x.required_types == set()
    x = d[('GLbyte', None)]
    assert isinstance(x, Type)
    assert x.name == 'GLbyte'
    assert x.template == 'typedef signed char {name};'
    assert x.api is None
    assert x.required_types == set()
    x = d[('GLbyte', 'gles2')]
    assert isinstance(x, Type)
    assert x.name == 'GLbyte'
    assert x.template == 'typedef khronos_int8_t {name};'
    assert x.api == 'gles2'
    assert x.required_types == set(['khrplatform'])


def test_load_enums():
    contents = r'''<?xml version="1.0" encoding="UTF-8" ?>
    <registry>
    <enums namespace="GL" start="0x0000" end="0x7FFF" vendor="ARB">
    <enum value="0x0000" name="GL_POINTS"/>
    </enums>
    <enums namespace="GL" vendor="ARB">
    <enum value="0x806F" name="GL_TEXTURE_3D"/>
    </enums>
    </registry>
    '''
    root = xml.etree.ElementTree.fromstring(contents)
    d = _load_enums(root)
    assert isinstance(d, dict)
    assert len(d) == 2
    x = d['GL_POINTS']
    assert isinstance(x, Enum)
    assert x.name == 'GL_POINTS'
    assert x.value == '0x0000'
    x = d['GL_TEXTURE_3D']
    assert isinstance(x, Enum)
    assert x.name == 'GL_TEXTURE_3D'
    assert x.value == '0x806F'


def test_load_commands():
    contents = r'''<?xml version="1.0" encoding="UTF-8" ?>
    <registry><commands namespace="GL">
    <command>
    <proto>void <name>glBufferData</name></proto>
    <param
    group="BufferTargetARB"><ptype>GLenum</ptype> <name>target</name></param>
    <param
    group="BufferSize"><ptype>GLsizeiptr</ptype> <name>size</name></param>
    <param len="size">const void *<name>data</name></param>
    <param
    group="BufferUsageARB"><ptype>GLenum</ptype> <name>usage</name></param>
    </command>
    </commands></registry>
    '''
    root = xml.etree.ElementTree.fromstring(contents)
    d = _load_commands(root)
    assert isinstance(d, dict)
    assert len(d) == 1
    x = d['glBufferData']
    assert isinstance(x, Command)
    assert x.name == 'glBufferData'
    assert x.proto_template == 'void {name}'
    y = x.params
    assert isinstance(y, list)
    assert len(y) == 4
    z = y[0]
    assert isinstance(z, Param)
    assert z.name == 'target'
    assert z.template == 'GLenum {name}'
    z = y[1]
    assert isinstance(z, Param)
    assert z.name == 'size'
    assert z.template == 'GLsizeiptr {name}'
    z = y[2]
    assert isinstance(z, Param)
    assert z.name == 'data'
    assert z.template == 'const void *{name}'
    z = y[3]
    assert isinstance(z, Param)
    assert z.name == 'usage'
    assert z.template == 'GLenum {name}'
    x.required_types = set(['GLenum', 'GLsizeiptr'])


def test_load_features():
    contents = r'''<?xml version="1.0" encoding="UTF-8" ?>
    <registry>
    <feature api="gl" name="GL_VERSION_3_2" number="3.2">
        <require>
            <type name="GLbyte"/>
            <enum name="GL_GEOMETRY_SHADER"/>
        </require>
        <require>
            <enum name="GL_DEPTH_CLAMP"/>
            <command name="glDrawElementsBaseVertex"/>
        </require>
        <remove profile="core">
            <command name="glNewList"/>
            <command name="glEndList"/>
        </remove>
        <remove profile="core">
            <enum name="GL_POINT_BIT"/>
            <command name="glArrayElement"/>
        </remove>
    </feature>
    </registry>
    '''
    root = xml.etree.ElementTree.fromstring(contents)
    d = _load_features(root)
    assert isinstance(d, dict)
    assert len(d) == 1
    x = d['GL_VERSION_3_2']
    assert isinstance(x, Feature)
    assert x.name == 'GL_VERSION_3_2'
    assert x.api == 'gl'
    assert x.number == (3, 2)
    requires = x.requires
    assert isinstance(requires, list)
    assert len(requires) == 2
    y = requires[0]
    assert isinstance(y, Require)
    assert y.types == set(['GLbyte'])
    assert y.enums == set(['GL_GEOMETRY_SHADER'])
    assert y.commands == set()
    assert y.profile is None
    assert y.api is None
    y = requires[1]
    assert isinstance(y, Require)
    assert y.types == set()
    assert y.enums == set(['GL_DEPTH_CLAMP'])
    assert y.commands == set(['glDrawElementsBaseVertex'])
    assert y.profile is None
    assert y.api is None
    removes = x.removes
    assert isinstance(removes, list)
    assert len(removes) == 2
    y = removes[0]
    assert isinstance(y, Remove)
    assert y.types == set()
    assert y.enums == set()
    assert y.commands == set(['glNewList', 'glEndList'])
    assert y.profile == 'core'
    y = removes[1]
    assert isinstance(y, Remove)
    assert y.types == set()
    assert y.enums == set(['GL_POINT_BIT'])
    assert y.commands == set(['glArrayElement'])
    assert y.profile == 'core'


def test_load_extensions():
    contents = r'''<?xml version="1.0" encoding="UTF-8" ?>
    <registry><extensions>
    <extension name="GL_OES_EGL_image" supported="gles1|gles2">
        <require>
            <type name="GLeglImageOES"/>
            <command name="glEGLImageTargetTexture2DOES"/>
            <command name="glEGLImageTargetRenderbufferStorageOES"/>
        </require>
        <require api="gles2">
            <enum name="GL_SAMPLER_EXTERNAL_OES"/>
        </require>
    </extension>
    </extensions></registry>
    '''
    root = xml.etree.ElementTree.fromstring(contents)
    d = _load_extensions(root)
    assert isinstance(d, dict)
    assert len(d) == 1
    x = d['GL_OES_EGL_image']
    assert x.name == 'GL_OES_EGL_image'
    assert x.supported == set(['gles1', 'gles2'])
    requires = x.requires
    assert isinstance(requires, list)
    assert len(requires) == 2
    y = requires[0]
    assert isinstance(y, Require)
    assert y.types == set(['GLeglImageOES'])
    assert y.enums == set()
    assert y.commands == set(['glEGLImageTargetTexture2DOES',
                             'glEGLImageTargetRenderbufferStorageOES'])
    assert y.profile is None
    assert y.api is None
    y = requires[1]
    assert isinstance(y, Require)
    assert y.types == set()
    assert y.enums == set(['GL_SAMPLER_EXTERNAL_OES'])
    assert y.commands == set()
    assert y.profile is None
    assert y.api == 'gles2'


def main(args, prog=None):
    """Generates a C header file"""
    prog = prog if prog is not None else sys.argv[0]
    # Prevent broken pipe exception from being raised.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
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
    p.add_argument('registry', type=argparse.FileType('rb'))
    args = p.parse_args(args)
    o = args.output
    try:
        registry = load(args.registry)
        if args.list_apis:
            for x in sorted(get_apis(registry)):
                print(x, file=o)
            return 0
        elif args.list_profiles:
            for x in sorted(get_profiles(registry)):
                print(x, file=o)
            return 0
        elif args.list_supports:
            for x in sorted(get_extension_support_strings(registry)):
                print(x, file=o)
            return 0
        apis = generate_api(registry, profile=args.profile, api=args.api,
                            extension_support=args.support)
        for api in apis:
            print('#ifndef', api.name, file=o)
            print('#define', api.name, file=o)
            for k, v in api.types.items():
                print(v.template.format(name=v.name, apientry=''), file=o)
            api_enums = sorted(api.enums.items(), key=lambda x: x[1].value)
            for k, v in api_enums:
                print('#define', k, v.value, file=o)
            api_cmds = sorted(api.commands.items(), key=lambda x: x[0])
            for k, v in api_cmds:
                params = ', '.join(x.text for x in v.params)
                print('extern ', v.proto_text, '(', params, ');', sep='',
                      file=o)
            for k, v in api_cmds:
                params = ', '.join(x.text for x in v.params)
                name = '(*PFN{0}PROC)'.format(k.upper())
                print('typedef ', v.proto_template.format(name=name), '(',
                      params, ');', sep='', file=o)
            print('#endif', file=o)
            print('', file=o)
    except:
        e = sys.exc_info()[1]
        print(prog, ': error: ', e, sep='', file=sys.stderr)
        raise
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:], sys.argv[0]))
