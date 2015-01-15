Release Notes
==============
.. currentmodule:: glreg

0.9.0a3
--------
* Critical fix for the bug :func:`group_apis` which caused it to not return
  anything because wrong arguments were passed to :func:`import_extension`
  and :func:`import_feature`.
* New attribute :attr:`Type.type` to account for Type's return type, if
  provided. This is reflected in :attr:`Type.required_types`. This change
  fixes the behavior of the registry import API functions.
* :attr:`Command.text` has trailing ``;`` removed.
* The default list of extensions in :func:`group_apis` are now sorted in the
  sort order used in the official OpenGL headers.

0.9.0a2
--------
* Minor metadata changes for PyPI upload

0.9.0a1
--------
First release. Hello world!
