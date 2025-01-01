# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.heancms import HeanCMS


def convert_old_slug(slug):
    slug = slug.split('-')
    last_chunk = slug[-1]
    if last_chunk.isdigit() and int(last_chunk) > 10**10:
        return '-'.join(slug[:-1])


class Perfscan(HeanCMS):
    id = 'perfscan'
    name = 'Perf Scan'
    lang = 'fr'
    status = 'disabled'

    has_cf = True

    base_url = 'https://perf-scan.fr'
    api_url = 'https://api.perf-scan.fr'

    cover_css_path = '#content div.container:first-child > div > div:last-child img'
    authors_css_path = 'div.flex:-soup-contains("Auteur") > span:last-child'
    synopsis_css_path = '.datas_synopsis, #content p'  # 2 page types!

    def get_manga_data(self, initial_data):
        if new_slug := convert_old_slug(initial_data['slug']):
            initial_data['slug'] = new_slug

        return HeanCMS.get_manga_data(self, initial_data)
