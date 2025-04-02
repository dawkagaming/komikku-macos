# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json

from bs4 import BeautifulSoup

from komikku.servers.multi.heancms import extract_info_from_script
from komikku.servers.multi.heancms import HeanCMS
from komikku.utils import get_buffer_mime_type


class Ezmanga(HeanCMS):
    id = 'ezmanga'
    name = 'EZmanga'
    lang = 'en'

    base_url = 'https://ezmanga.org'
    logo_url = base_url + '/favicon.ico'
    api_url = 'https://api.ezmanga.org'
    api_version = 1

    name_css_path = 'h2'
    cover_css_path = 'img[width="500"]'
    authors_css_path = 'div.flex:-soup-contains("Author") > span:last-child'
    synopsis_css_path = 'p'

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

        if info := extract_info_from_script(soup, 'API_Response'):
            info = json.loads(info)
            images = info[0][3]['API_Response']['chapter']['chapter_data']['images']

            data = dict(
                pages=[],
            )
            for url in images:
                data['pages'].append(dict(
                    slug=None,
                    image=url,
                ))

            return data

        return None
