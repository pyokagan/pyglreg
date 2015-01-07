import collections
import sys
import xml.etree.ElementTree
import unittest
import io
import tempfile
import glreg
from glreg import *

_test_reg = r'''<?xml version="1.0" encoding="UTF-8" ?>
    <registry>
    <types>
    <type name="stddef">#include &lt;stddef.h&gt;</type>
    <type name="khrplatform">#include &lt;KHR/khrplatform.h&gt;</type>
    <type>typedef unsigned int <name>GLenum</name>;</type>
    <type>typedef signed char <name>GLbyte</name>; {}</type>
    <type requires="stddef">typedef ptrdiff_t <name>GLsizeiptr</name>;</type>
    <type api="gles2"
    requires="khrplatform">typedef khronos_int8_t <name>GLbyte</name>;</type>
    </types>
    <enums namespace="GL" start="0x0000" end="0x7FFF" vendor="ARB">
    <enum value="0x0000" name="GL_POINTS"/>
    </enums>
    <enums namespace="GL" vendor="ARB">
    <enum value="0x806F" name="GL_TEXTURE_3D"/>
    </enums>
    <commands namespace="GL">
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
    </commands>
    <feature api="gl" name="GL_VERSION_3_2" number="3.2">
        <require>
            <type name="GLbyte"/>
            <enum name="GL_POINTS"/>
        </require>
        <require>
            <enum name="GL_TEXTURE_3D"/>
            <command name="glBufferData"/>
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
    <extensions>
    <extension name="GL_ARB_vertex_buffer_object" supported="gl">
    <require>
        <command name="glBufferData"/>
    </require>
    </extension>
    </extensions>
    </registry>
'''


class TestLoadFunctions(unittest.TestCase):
    def test_load_types(self, types=None):
        if types is None:
            root = xml.etree.ElementTree.fromstring(_test_reg)
            types = glreg._load_types(root)
        self.assertIsInstance(types, collections.OrderedDict)
        self.assertEqual(len(types), 6)
        items = list(types.items())
        k, x = items[2]
        self.assertEqual(k, ('GLenum', None))
        self.assertIsInstance(x, Type)
        self.assertEqual(x.name, 'GLenum')
        self.assertEqual(x.template, 'typedef unsigned int {name};')
        self.assertEqual(x.text, 'typedef unsigned int GLenum;')
        self.assertIsNone(x.api)
        self.assertEqual(x.required_types, set())
        k, x = items[3]
        self.assertEqual(k, ('GLbyte', None))
        self.assertIsInstance(x, Type)
        self.assertEqual(x.name, 'GLbyte')
        self.assertEqual(x.template, 'typedef signed char {name}; {{}}')
        self.assertIsNone(x.api)
        self.assertEqual(x.required_types, set())
        k, x = items[5]
        self.assertEqual(k, ('GLbyte', 'gles2'))
        self.assertIsInstance(x, Type)
        self.assertEqual(x.name, 'GLbyte')
        self.assertEqual(x.template, 'typedef khronos_int8_t {name};')
        self.assertEqual(x.api, 'gles2')
        self.assertEqual(x.required_types, {'khrplatform'})

    def test_load_enums(self, enums=None):
        if enums is None:
            root = xml.etree.ElementTree.fromstring(_test_reg)
            enums = glreg._load_enums(root)
        self.assertIsInstance(enums, collections.OrderedDict)
        self.assertEqual(len(enums), 2)
        x = enums['GL_POINTS']
        self.assertIsInstance(x, Enum)
        self.assertEqual(x.name, 'GL_POINTS')
        self.assertEqual(x.value, '0x0000')
        x = enums['GL_TEXTURE_3D']
        self.assertIsInstance(x, Enum)
        self.assertEqual(x.name, 'GL_TEXTURE_3D')
        self.assertEqual(x.value, '0x806F')

    def test_load_commands(self, commands=None):
        if commands is None:
            root = xml.etree.ElementTree.fromstring(_test_reg)
            commands = glreg._load_commands(root)
        self.assertIsInstance(commands, collections.OrderedDict)
        self.assertEqual(len(commands), 1)
        x = commands['glBufferData']
        self.assertIsInstance(x, Command)
        self.assertEqual(x.name, 'glBufferData')
        self.assertEqual(x.proto_template, 'void {name}')
        y = x.params
        self.assertIsInstance(y, list)
        self.assertEqual(len(y), 4)
        z = y[0]
        self.assertIsInstance(z, Param)
        self.assertEqual(z.name, 'target')
        self.assertEqual(z.type, 'GLenum')
        self.assertEqual(z.template, '{type} {name}')
        z = y[1]
        self.assertIsInstance(z, Param)
        self.assertEqual(z.name, 'size')
        self.assertEqual(z.type, 'GLsizeiptr')
        self.assertEqual(z.template, '{type} {name}')
        z = y[2]
        self.assertIsInstance(z, Param)
        self.assertEqual(z.name, 'data')
        self.assertEqual(z.type, None)
        self.assertEqual(z.template, 'const void *{name}')
        z = y[3]
        self.assertIsInstance(z, Param)
        self.assertEqual(z.name, 'usage')
        self.assertEqual(z.type, 'GLenum')
        self.assertEqual(z.template, '{type} {name}')
        self.assertEqual(x.required_types, {'GLenum', 'GLsizeiptr'})

    def test_load_features(self, features=None):
        if features is None:
            root = xml.etree.ElementTree.fromstring(_test_reg)
            features = glreg._load_features(root)
        self.assertIsInstance(features, collections.OrderedDict)
        self.assertEqual(len(features), 1)
        x = features['GL_VERSION_3_2']
        self.assertIsInstance(x, Feature)
        self.assertEqual(x.name, 'GL_VERSION_3_2')
        self.assertEqual(x.api, 'gl')
        self.assertEqual(x.number, (3, 2))
        requires = x.requires
        self.assertIsInstance(requires, list)
        self.assertEqual(len(requires), 2)
        y = requires[0]
        self.assertIsInstance(y, Require)
        self.assertEqual(y.types, ['GLbyte'])
        self.assertEqual(y.enums, ['GL_POINTS'])
        self.assertEqual(y.commands, [])
        self.assertIsNone(y.profile)
        self.assertIsNone(y.api)
        y = requires[1]
        self.assertIsInstance(y, Require)
        self.assertEqual(y.types, [])
        self.assertEqual(y.enums, ['GL_TEXTURE_3D'])
        self.assertEqual(y.commands, ['glBufferData'])
        self.assertIsNone(y.profile)
        self.assertIsNone(y.api)
        removes = x.removes
        self.assertIsInstance(removes, list)
        self.assertEqual(len(removes), 2)
        y = removes[0]
        self.assertIsInstance(y, Remove)
        self.assertEqual(y.types, [])
        self.assertEqual(y.enums, [])
        self.assertEqual(y.commands, ['glNewList', 'glEndList'])
        self.assertEqual(y.profile, 'core')
        y = removes[1]
        self.assertIsInstance(y, Remove)
        self.assertEqual(y.types, [])
        self.assertEqual(y.enums, ['GL_POINT_BIT'])
        self.assertEqual(y.commands, ['glArrayElement'])
        self.assertEqual(y.profile, 'core')

    def test_load_extensions(self, extensions=None):
        if extensions is None:
            root = xml.etree.ElementTree.fromstring(_test_reg)
            extensions = glreg._load_extensions(root)
        self.assertIsInstance(extensions, collections.OrderedDict)
        self.assertEqual(len(extensions), 1)
        x = extensions['GL_ARB_vertex_buffer_object']
        self.assertEqual(x.name, 'GL_ARB_vertex_buffer_object')
        self.assertEqual(x.supported, {'gl'})
        requires = x.requires
        self.assertIsInstance(requires, list)
        self.assertEqual(len(requires), 1)
        y = requires[0]
        self.assertIsInstance(y, Require)
        self.assertEqual(y.types, [])
        self.assertEqual(y.enums, [])
        self.assertEqual(y.commands, ['glBufferData'])
        self.assertIsNone(y.profile)
        self.assertIsNone(y.api)

    def test_load(self):
        if sys.version_info > (3, 0):
            f = io.StringIO(_test_reg)
        else:
            f = io.BytesIO(_test_reg)
        registry = load(f)
        self.test_load_types(registry.types)
        self.test_load_enums(registry.enums)
        self.test_load_commands(registry.commands)
        self.test_load_features(registry.features)
        self.test_load_extensions(registry.extensions)

    def test_loads(self):
        registry = loads(_test_reg)
        self.test_load_types(registry.types)
        self.test_load_enums(registry.enums)
        self.test_load_commands(registry.commands)
        self.test_load_features(registry.features)
        self.test_load_extensions(registry.extensions)


class TestRegistry(unittest.TestCase):
    """Test Registy interface"""

    def setUp(self):
        self.src = loads(_test_reg)

    def test_get_requires(self):
        requires = self.src.get_requires()
        self.assertIsInstance(requires, list)
        self.assertEqual(len(requires), 3)

    def test_get_removes(self):
        removes = self.src.get_removes()
        self.assertIsInstance(removes, list)
        # NOTE: No Remove objects are returned because we did
        # not specify any api or profile, and thus no Removals
        # are active.
        self.assertEqual(len(removes), 0)

    def test_get_profiles(self):
        profiles = self.src.get_profiles()
        self.assertIsInstance(profiles, set)
        self.assertEqual(profiles, {'core'})

    def test_get_apis(self):
        apis = self.src.get_apis()
        self.assertIsInstance(apis, set)
        self.assertEqual(apis, {'gl', 'gles2'})

    def test_get_supports(self):
        supports = self.src.get_supports()
        self.assertIsInstance(supports, set)
        self.assertEqual(supports, {'gl'})


class TestImportFunctions(unittest.TestCase):
    def setUp(self):
        self.src = loads(_test_reg)
        self.dst = Registry()

    def test_import_type(self):
        import_type(self.dst, self.src, 'GLbyte', 'gles2')
        stypes = self.src.types
        dtypes = self.dst.types
        self.assertIsInstance(dtypes, collections.OrderedDict)
        self.assertEqual(len(dtypes), 2)
        items = list(dtypes.items())
        _, x = items[0]
        self.assertIs(x, stypes[('khrplatform', None)])
        _, x = items[1]
        self.assertIs(x, stypes[('GLbyte', 'gles2')])

    def test_import_enum(self):
        import_enum(self.dst, self.src, 'GL_POINTS')
        enums = self.dst.enums
        assert isinstance(enums, collections.OrderedDict)
        assert len(enums) == 1
        items = list(enums.items())
        _, x = items[0]
        assert isinstance(x, Enum)
        assert x.name == 'GL_POINTS'
        assert x.value == '0x0000'

    def test_import_command(self):
        import_command(self.dst, self.src, 'glBufferData')
        stypes = self.src.types
        dtypes = self.dst.types
        self.assertIsInstance(dtypes, collections.OrderedDict)
        self.assertEqual(len(dtypes), 3)
        self.assertIs(dtypes[('stddef', None)], stypes[('stddef', None)])
        self.assertIs(dtypes[('GLenum', None)], stypes[('GLenum', None)])
        self.assertIs(dtypes[('GLsizeiptr', None)],
                      stypes[('GLsizeiptr', None)])
        scmds = self.src.commands
        dcmds = self.dst.commands
        self.assertIsInstance(dcmds, collections.OrderedDict)
        self.assertEqual(len(dcmds), 1)
        self.assertEqual(dcmds['glBufferData'], scmds['glBufferData'])

    def test_import_feature(self):
        dtypes = self.dst.types
        denums = self.dst.enums
        dcmds = self.dst.commands
        import_feature(self.dst, self.src, 'GL_VERSION_3_2')
        # Test types import
        stypes = self.src.types
        self.assertIsInstance(dtypes, collections.OrderedDict)
        self.assertEqual(len(dtypes), 4)
        self.assertIs(dtypes[('stddef', None)], stypes[('stddef', None)])
        self.assertIs(dtypes[('GLenum', None)], stypes[('GLenum', None)])
        self.assertIs(dtypes[('GLsizeiptr', None)],
                      stypes[('GLsizeiptr', None)])
        self.assertIs(dtypes[('GLbyte', None)], stypes[('GLbyte', None)])
        # Test enums import
        senums = self.src.enums
        self.assertIsInstance(denums, collections.OrderedDict)
        self.assertEqual(len(denums), 2)
        self.assertIs(denums['GL_POINTS'], senums['GL_POINTS'])
        self.assertIs(denums['GL_TEXTURE_3D'], senums['GL_TEXTURE_3D'])
        # Test commands import
        scmds = self.src.commands
        self.assertIsInstance(dcmds, collections.OrderedDict)
        self.assertEqual(len(dcmds), 1)
        self.assertIs(dcmds['glBufferData'], scmds['glBufferData'])

    def test_import_extension(self):
        dtypes = self.dst.types
        dcmds = self.dst.commands
        import_extension(self.dst, self.src, 'GL_ARB_vertex_buffer_object')
        # Test types import
        stypes = self.src.types
        self.assertIsInstance(dtypes, collections.OrderedDict)
        self.assertEqual(len(dtypes), 3)
        self.assertIs(dtypes[('stddef', None)], stypes[('stddef', None)])
        self.assertIs(dtypes[('GLenum', None)], stypes[('GLenum', None)])
        self.assertIs(dtypes[('GLsizeiptr', None)],
                      stypes[('GLsizeiptr', None)])
        # Test commands import
        scmds = self.src.commands
        self.assertIsInstance(dcmds, collections.OrderedDict)
        self.assertEqual(len(dcmds), 1)
        self.assertIs(dcmds['glBufferData'], scmds['glBufferData'])

    def test_import_registry(self):
        dtypes = self.dst.types
        denums = self.dst.enums
        dcmds = self.dst.commands
        import_registry(self.dst, self.src)
        # Test types import
        stypes = self.src.types
        self.assertIsInstance(dtypes, collections.OrderedDict)
        self.assertEqual(len(dtypes), 4)
        self.assertIs(dtypes[('stddef', None)], stypes[('stddef', None)])
        self.assertIs(dtypes[('GLenum', None)], stypes[('GLenum', None)])
        self.assertIs(dtypes[('GLsizeiptr', None)],
                      stypes[('GLsizeiptr', None)])
        self.assertIs(dtypes[('GLbyte', None)], stypes[('GLbyte', None)])
        # Test enums import
        senums = self.src.enums
        self.assertIsInstance(denums, collections.OrderedDict)
        self.assertEqual(len(denums), 2)
        self.assertIs(denums['GL_POINTS'], senums['GL_POINTS'])
        self.assertIs(denums['GL_TEXTURE_3D'], senums['GL_TEXTURE_3D'])
        # Test commands import
        scmds = self.src.commands
        self.assertIsInstance(scmds, collections.OrderedDict)
        self.assertEqual(len(dcmds), 1)
        self.assertIs(dcmds['glBufferData'], scmds['glBufferData'])


class TestGroupAPIS(unittest.TestCase):
    def test_group_apis(self):
        reg = loads(_test_reg)
        stypes = reg.types
        senums = reg.enums
        scmds = reg.commands
        apis = group_apis(reg)
        self.assertIsInstance(apis, list)
        self.assertEqual(len(apis), 2)
        # Test for first API (GL_VERSION_3_2)
        api = apis[0]
        self.assertIsInstance(api, Registry)
        # Test types
        dtypes = api.types
        self.assertIsInstance(dtypes, collections.OrderedDict)
        self.assertEqual(len(dtypes), 4)
        # Test enums
        denums = api.enums
        self.assertIsInstance(denums, collections.OrderedDict)
        self.assertEqual(len(denums), 2)
        # Test commands
        dcmds = api.commands
        self.assertIsInstance(dcmds, collections.OrderedDict)
        self.assertEqual(len(dcmds), 1)
        # Test for second API (GL_ARB_vertex_buffer_object)
        api = apis[1]
        self.assertIsInstance(api, Registry)
        # Test types
        dtypes = api.types
        self.assertIsInstance(dtypes, collections.OrderedDict)
        self.assertEqual(len(dtypes), 0)
        # Test enums
        denums = api.enums
        self.assertIsInstance(denums, collections.OrderedDict)
        self.assertEqual(len(denums), 0)
        # Test commands
        dcmds = api.commands
        self.assertIsInstance(dcmds, collections.OrderedDict)
        self.assertEqual(len(dcmds), 0)


class TestMain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fin = tempfile.NamedTemporaryFile('w')
        cls.fin.write(_test_reg)
        cls.fin.flush()

    def setUp(self):
        self.fout = tempfile.NamedTemporaryFile('r')

    def test_main(self):
        glreg.main(['-o', self.fout.name, self.fin.name])

    def test_main_list_apis(self):
        glreg.main(['-o', self.fout.name, '--list-apis', self.fin.name])

    def test_main_list_profiles(self):
        glreg.main(['-o', self.fout.name, '--list-profiles', self.fin.name])

    def test_main_list_supports(self):
        glreg.main(['-o', self.fout.name, '--list-supports', self.fin.name])
