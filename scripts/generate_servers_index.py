#! /usr/bin/env python

import glob
import hashlib
import json
import os

data = []
dirpath = 'komikku/servers'

# Walk in servers folder
for file in glob.glob('komikku/servers/*/*.py'):
    with open(file, 'r') as fp:
        hash = hashlib.sha256(fp.read().encode()).hexdigest()

    data.append({
        'file': file.replace(dirpath, '')[1:],
        'hash': hash,
    })

with open(os.path.join(dirpath, 'index.json'), 'w+') as fp:
    json.dump(data, fp, indent=2)
