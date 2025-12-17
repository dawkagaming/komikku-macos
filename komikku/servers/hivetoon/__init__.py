# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import logging

from bs4 import BeautifulSoup

from komikku.servers.multi.heancms import HeanCMS
from komikku.servers.utils import parse_nextjs_hydration
from komikku.utils import get_buffer_mime_type

logger = logging.getLogger(__name__)


class Hivetoon(HeanCMS):
    id = 'hivetoon'
    name = 'Hive Toon'
    lang = 'en'

    base_url = 'https://hivetoons.org'
    logo_url = 'https://storage.hivetoon.com/public/upload/2024/12/05/logo-end-1 (1)-09f57d7d7ea3f031.webp'
    api_url = 'https://api.hivetoons.org/api'

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Pages URLs are available in a <script> element
        """
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

        if info := parse_nextjs_hydration(soup, 'images'):
            images = info[3]['children'][1][3]['children'][3]['children'][1][3]['children'][3]['children'][3]['chapter']['images']

            data = dict(
                pages=[],
            )
            for image in images:
                data['pages'].append(dict(
                    slug=None,
                    image=image['url'],
                ))

            return data

        return None
