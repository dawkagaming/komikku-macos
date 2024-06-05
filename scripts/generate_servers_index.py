#! /usr/bin/env python

import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from komikku.servers import APP_MIN_VERSION

data = {
    'app_min_version': APP_MIN_VERSION,
    'modules': {},
}
dirpath = 'komikku/servers'

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
