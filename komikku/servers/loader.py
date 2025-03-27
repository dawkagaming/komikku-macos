# SPDX-FileCopyrightText: 2021-2024 Liliana Prikler
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>
# Author: Liliana Prikler <liliana.prikler@gmail.com>

from enum import IntEnum
import importlib.abc
import importlib.machinery
import os
import sys
import types


class ServerFinderPriority(IntEnum):
    # Defines the position of the Finder in the meta path finder list
    LOW = 1   # added at end
    HIGH = 2  # added at beginning


class ServerFinder(importlib.abc.MetaPathFinder):
    _PREFIX = 'komikku.servers.'

    def __init__(self, priority=ServerFinderPriority.LOW):
        self._paths = []
        self.priority = priority

    @property
    def paths(self):
        return self._paths

    def add_path(self, path):
        if not isinstance(path, str):
            return

        path = os.path.abspath(path)
        if not os.path.exists(path):
            return

        self._paths.append(path)

    def find_spec(self, fullname, path, target=None):
        """Attempt to locate the requested module

        fullname is the fully-qualified name of the module,
        path is set to parent package __path__ for sub-modules/packages or None otherwise,
        target can be a module object but is unused here.
        """
        if not fullname.startswith(self._PREFIX):
            return None

        name = fullname[len(self._PREFIX):]
        base_dir = name.replace('.', '/')
        for path in self._paths:
            candidate_path = os.path.join(path, base_dir, '__init__.py')
            if os.path.exists(candidate_path):
                return importlib.machinery.ModuleSpec(
                    fullname,
                    ServerLoader(fullname, candidate_path),
                    origin=candidate_path,
                )

        return None

    def install(self):
        if self._paths and self not in sys.meta_path:
            if self.priority == ServerFinderPriority.HIGH:
                sys.meta_path = [self] + sys.meta_path
            else:
                sys.meta_path = sys.meta_path + [self]


class ServerLoader(importlib.machinery.SourceFileLoader):
    def create_module(self, spec):
        """Create the given module from the supplied module spec"""

        module = types.ModuleType(spec.name)

        # Compare and contrast _new_module in importlib._bootstrap
        # We set the file name early, because we only load real files anyway,
        # see ServerFinder.find_spec, and because it helps locating relative files, such as logos.
        module.__file__ = spec.origin
        if not self.get_source(spec.name):
            # __path__ must be set to make packages with empty `__init__.py` loadable, such as `multi` package
            module.__path__ = [os.path.dirname(spec.origin)]

        return module
