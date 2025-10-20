#! /usr/bin/env python3

# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

"""
Allow to obtain a version that does not use WebKitGtk.

This results in the removal of a number of servers and trackers that depend on it.

Modifications:
- Remove the application's WebView page and all utility functions using WebView
- Remove all servers and trackers dependent on WebView
- Remove usage of WebView in all multi servers
- Hide the `WebView` and `Servers Modules` sections in `Preferences -> Advanced`
"""

import glob
import os
import shutil

files_to_delete = [
    'komikku/webview.py',
    'data/ui/webview.blp',
]
files_to_clean = [
    'komikku/application.py',
    'komikku/debug_info.py',
    'data/info.febvre.Komikku.gresource.xml.in',
    'data/meson.build',
]
ui_files_with_widgets_to_hide = [
    'data/ui/preferences.blp',
]
folders_to_delete = []
multi_servers_to_clean = []


def get_servers_and_trackers_to_delete():
    pathnames = ['komikku/servers/*/', 'komikku/trackers/*/']
    for pathname in pathnames:
        for module_path in glob.glob(pathname):
            if module_path.endswith(('multi/', '__pycache__/')):
                continue

            with open(os.path.join(module_path, '__init__.py'), 'r') as fp:
                content = fp.read()
                if 'webview' in content:
                    folders_to_delete.append(module_path)


def get_multi_servers_to_clean():
    # Walk in multi servers folder
    pathname = 'komikku/servers/multi/*/'
    for module_path in glob.glob(pathname):
        if module_path.endswith('__pycache__/'):
            continue

        with open(os.path.join(module_path, '__init__.py'), 'r') as fp:
            content = fp.read()
            if 'webview' in content:
                multi_servers_to_clean.append(os.path.join(module_path, '__init__.py'))


def hide_widgets(filepath, keywords):
    with open(filepath, 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        f.truncate()
        for line in lines:
            for keyword in keywords:
                if keyword in line:
                    f.write('visible: false;\n')
                    break

            f.write(line)


def remove_lines_by_keywords(filepath, keywords):
    with open(filepath, 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        f.truncate()
        for line in lines:
            keep = True
            for keyword in keywords:
                if keyword in line:
                    keep = False
                    break

            if keep:
                f.write(line)


def main():
    get_servers_and_trackers_to_delete()
    get_multi_servers_to_clean()

    for path_ in files_to_delete:
        print('Remove file', path_)
        if os.path.exists(path_):
            os.unlink(path_)

    for path_ in folders_to_delete:
        print('Remove folder', path_)
        shutil.rmtree(path_)

    for path_ in files_to_clean:
        print('Clean file', path_)
        remove_lines_by_keywords(path_, ['webview', 'WebKit'])

    for path_ in multi_servers_to_clean:
        print('Clean file', path_)
        remove_lines_by_keywords(path_, ['webview', 'CompleteChallenge'])

    for path_ in ui_files_with_widgets_to_hide:
        print('Hide widgets', path_)
        hide_widgets(path_, ['title: _("WebView")', 'title: _("Servers Modules")'])


if __name__ == '__main__':
    main()
