# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara
from komikku.servers.multi.manga_stream import MangaStream


class Asurascans(MangaStream):
    id = 'asurascans'
    name = 'Asura Scans'
    lang = 'en'

    base_url = 'https://asura-scan.com'

    authors_selector = '.infox .fmed:-soup-contains("Artist") span, .infox .fmed:-soup-contains("Author") span'
    genres_selector = '.infox .mgen a'
    scanlators_selector = '.infox .fmed:-soup-contains("Serialization") span'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'

    ignored_pages = ['page100-10.jpg', 'zzzzzzz999999.jpg', ]

    def check_slug(self, initial_data):
        # A random number is always prepended to slug and it changes regularly
        # Try to retrieve new slug
        res = self.search(initial_data['name'], '')
        if not res:
            return None

        for item in res:
            base_slug = '-'.join(initial_data['slug'].split('-')[1:])
            current_base_slug = '-'.join(item['slug'].split('-')[1:])
            if current_base_slug in (initial_data['slug'], base_slug) and initial_data['slug'] != item['slug']:
                return item['slug']

        return None

    def get_manga_data(self, initial_data):
        if new_slug := self.check_slug(initial_data):
            initial_data['slug'] = new_slug

        return MangaStream.get_manga_data(self, initial_data)


class Asurascans_tr(Madara):
    id = 'asurascans_tr'
    name = 'Armoni Scans (Asura Scans)'
    lang = 'tr'

    date_format = '%d %B %Y'

    base_url = 'https://asurascans.com.tr'
