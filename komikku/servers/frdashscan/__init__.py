# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json
import re

from bs4 import BeautifulSoup

from komikku.servers.multi.madara import Madara
from komikku.utils import get_buffer_mime_type


class Frdashscan(Madara):
    id = 'frdashscan'
    name = 'Fr-Scan'
    lang = 'fr'
    is_nsfw = True
    status = 'disabled'

    date_format = None

    base_url = 'https://fr-scan.com'
    chapter_url = base_url + '/manga/{0}/{1}/'  # don't support style param
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'

    images_regex = r'var chapter_preloaded_images *= *(\[.*\]).*'

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        r = self.session_get(
            self.chapter_url.format(manga_slug, chapter_slug),
            headers={
                'Referer': self.manga_url.format(manga_slug),
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        if script_element := soup.select_one('script#chapter_preloaded_images'):
            data = dict(
                pages=[],
            )

            script = script_element.string.strip()
            for line in script.split(';'):
                line = line.strip()
                if not line.startswith('var chapter_preloaded_images'):
                    continue

                line = line.replace('\\', '')
                if match := re.compile(self.images_regex).search(line):
                    for url in json.loads(match.group(1)):
                        data['pages'].append(dict(
                            slug=None,
                            image=url,
                        ))

                return data
        else:
            return Madara.get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url)
