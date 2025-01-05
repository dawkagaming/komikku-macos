# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import importlib
import inspect
import logging
from operator import itemgetter
import os
from pkgutil import iter_modules
import sys

logger = logging.getLogger(__name__)


def get_trackers_list(include_disabled=False, order_by=('name',)):
    trackers = []
    for module in get_trackers_modules():
        for _name, obj in dict(inspect.getmembers(module)).items():
            if not hasattr(obj, 'id') or not hasattr(obj, 'name'):
                continue
            if NotImplemented in (obj.id, obj.name):
                continue

            if not include_disabled and obj.status == 'disabled':
                continue

            if inspect.isclass(obj):
                logo_path = os.path.join(os.path.dirname(os.path.abspath(module.__file__)), obj.id + '.png')

                trackers.append(dict(
                    id=obj.id,
                    name=obj.name,
                    logo_path=logo_path if os.path.exists(logo_path) else None,
                    module=module,
                    class_name=obj.id.capitalize(),
                ))

    return sorted(trackers, key=itemgetter(*order_by))


def get_trackers_modules():
    def import_modules(namespace, modules, modules_names):
        count = 0
        for _finder, module_name, ispkg in iter_namespace(namespace):
            if module_name in modules_names or not ispkg:
                continue

            module = importlib.import_module(module_name)
            modules.append(module)
            modules_names.append(module_name)
            count += 1

        if count > 0:
            logger.info('Import {0} trackers modules'.format(count))

        return count

    def iter_namespace(ns_pkg):
        # Specifying the second argument (prefix) to iter_modules makes the
        # returned name an absolute name instead of a relative one. This allows
        # import_module to work without having to do additional modification to
        # the name.
        return iter_modules(ns_pkg.__path__, ns_pkg.__name__ + '.')

    modules = []
    modules_names = []
    for finder in sys.meta_path:
        import komikku.trackers

        import_modules(komikku.trackers, modules, modules_names)

    return modules
