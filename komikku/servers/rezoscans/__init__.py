# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import logging

from bs4 import BeautifulSoup

from komikku.servers.multi.heancms import HeanCMS
from komikku.servers.utils import parse_nextjs_hydration
from komikku.utils import get_buffer_mime_type

logger = logging.getLogger(__name__)


class Rezoscans(HeanCMS):
    id = 'rezoscans'
    name = 'Rezo Scans'
    lang = 'en'

    base_url = 'https://rezoscan.org'
    logo_url = 'https://storage.rezoscan.org/upload/2025/06/24/%D8%A7%D9%84%D9%84%D9%88%D8%BA%D9%88-9f96b7a917940f61.webp'
    api_url = 'https://api.rezoscan.org/api'

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
