# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import logging

from bs4 import BeautifulSoup

from komikku.servers.multi.heancms import HeanCMS
from komikku.servers.utils import parse_nextjs_hydration
from komikku.utils import get_buffer_mime_type

logger = logging.getLogger(__name__)


class Hijalascans(HeanCMS):
    id = 'hijalascans'
    name = 'Hijala Scans'
    lang = 'en'

    base_url = 'https://en-hijala.com'
    logo_url = 'https://storage.en-hijala.com/upload/2025/06/24/final-523b7e2e4fb3a659.webp'
    api_url = 'https://api.en-hijala.com/api'

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
