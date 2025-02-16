#! /usr/bin/env python3

# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import glob
import hashlib
import json
import os

dirpath = 'komikku/servers'

# Extract minimum app version to use modules
with open(os.path.join(dirpath, '__init__.py')) as fp:
    for line in fp.readlines():
        if line.startswith('APP_MIN_VERSION'):
            app_min_version = line.split()[2].strip().replace("'", '')
            if app_min_version == 'None':
                app_min_version = None
            break

data = {
    'app_min_version': app_min_version,
    'modules': {},
}

# Walk in servers folder
for pathname in ('komikku/servers/multi/*/', 'komikku/servers/*/'):
    for module_path in glob.glob(pathname):
        if module_path.endswith(('multi/', '__pycache__/')):
            continue

        with open(os.path.join(module_path, '__init__.py'), 'r') as fp:
            hash = hashlib.sha256(fp.read().encode()).hexdigest()

        id = '-'.join(module_path.split('/')[2:-1])
        module_info = {
            'path': module_path.replace(dirpath, '')[1:],
            'files': [],
            'hash': hash,
        }
        for file in glob.glob(f'{module_path}/*'):
            module_info['files'].append(os.path.basename(file))

        data['modules'][id] = module_info

with open(os.path.join(dirpath, 'index.json'), 'w+') as fp:
    json.dump(data, fp, indent=2)
