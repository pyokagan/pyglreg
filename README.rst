=========================================
pyglreg: OpenGL XML API Registry Parser 
=========================================

`glreg` provides functionality to parse and extract data from
`OpenGL XML API Registry`_ files. Types, enums and functions (commands) in
the registry can be enumerated and inspected. This module also provides
functions to resolve dependencies and filter APIs in the registry. This makes
it useful for generating OpenGL headers and loaders.

.. _OpenGL XML API Registry:
   https://cvs.khronos.org/svn/repos/ogl/trunk/doc/registry/public/api/gl.xml

Sample code
============
Import the module:

>>> import glreg

Load a Registry object from a file:

>>> registry = glreg.load(open('gl.xml'))

Generate a simple OpenGL ES 2 C header:

>>> for api in glreg.group_apis(registry, api='gles2', support='gles2'):
...     print('#ifndef ' + api.name)
...     print('#define ' + api.name)
...     print(api.text)
...     print('#endif')
#ifndef GL_ES_VERSION_2_0
#define GL_ES_VERSION_2_0
#include <KHR/khrplatform.h>
typedef khronos_int8_t GLbyte;
...

Requirements
=============
* Python 2.7+, 3.2+

License
========
MIT License
