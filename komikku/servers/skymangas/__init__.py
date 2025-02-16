# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import base64
import json

from bs4 import BeautifulSoup

from komikku.servers.multi.manga_stream import MangaStream
from komikku.utils import get_buffer_mime_type


class Skymangas(MangaStream):
    id = 'skymangas'
    name = 'SkyMangas'
    lang = 'es'
    is_nsfw = True

    base_url = 'https://skymangas.com'

    authors_selector = '.infox .fmed:-soup-contains("Artist") span, .infox .fmed:-soup-contains("Author") span'
    genres_selector = '.infox .mgen a'
    scanlators_selector = '.infox .fmed:-soup-contains("Serialization") span'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Pages URLs are encoded in JS
        """
        r = self.session_get(
            self.chapter_url.format(manga_slug=manga_slug, chapter_slug=chapter_slug),
            headers={
                'Referer': self.manga_url.format(manga_slug),
            })
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        # Pages are loaded via javascript
        for script in soup.select('script[src^="data:text/javascript;base64,"]'):
            decoded_pages = base64.b64decode(script.get('src')[28:]).decode()
            if 'ts_reader' not in decoded_pages:
                continue

            pages = json.loads(decoded_pages[14:-2])  # "ts_reader.run(...);"
            for source in pages['sources']:
                # Use first source
                for url in source['images']:
                    data['pages'].append(dict(
                        slug=None,
                        image=url,
                    ))
                break
            break

        return data
