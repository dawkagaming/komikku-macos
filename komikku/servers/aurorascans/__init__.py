# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json
import logging

from bs4 import BeautifulSoup

from komikku.servers.multi.heancms import extract_info_from_script
from komikku.servers.multi.heancms import HeanCMS
from komikku.utils import get_buffer_mime_type

logger = logging.getLogger(__name__)


class Aurorascans(HeanCMS):
    id = 'aurorascans'
    name = 'Aurora Scans'
    lang = 'en'
    status = 'disabled'  # Merged with Night Scans => Qi Scans

    base_url = 'https://aurorascans.com'
    logo_url = 'https://storage.aurorascans.com/public/upload/2025/01/26/JUST-TO-TRY-f17fe0b13caeba2c-16b03dbd7548f1a3.webp'
    api_url = 'https://api.aurorascans.com/api'

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

        if info := extract_info_from_script(soup, 'images'):
            info = json.loads(info)
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
