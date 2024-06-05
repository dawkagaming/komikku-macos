#! /usr/bin/env python3

# Create a ZIP archive of all modules: {dirpath}/servers.zip

import os
import zipfile

dirpath = 'komikku/servers'


with zipfile.ZipFile(os.path.join(dirpath, 'servers.zip'), 'w', zipfile.ZIP_DEFLATED) as zip:
    for root, _dirs, files in os.walk(dirpath):
        if root.endswith('__pycache__'):
            # Skip __pycache__ folders
            continue

        for file in files:
            if root == dirpath and file != 'index.json':
                # Skip files at root except index.json
                continue
            zip.write(os.path.join(root, file), os.path.join('/'.join(root.split('/')[2:]), file))
