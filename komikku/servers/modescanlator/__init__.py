# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json

from bs4 import BeautifulSoup

from komikku.servers.multi.heancms import extract_info_from_script
from komikku.servers.multi.heancms import HeanCMS
from komikku.servers.utils import get_buffer_mime_type


class Modescanlator(HeanCMS):
    id = 'modescanlator'
    name = 'Mode Scanlator'
    lang = 'pt_BR'

    base_url = 'https://modescanlator.com'
    api_url = 'https://api.modescanlator.com'

    cover_css_path = '#content div.container:first-child > div > div:last-child img'
    authors_css_path = 'div.flex:-soup-contains("Author") > span:last-child'
    synopsis_css_path = 'div.text-muted-foreground > div:nth-child(1)'

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

            data = dict(
                pages=[],
            )
            for url in info[1][3]['children'][1][3]['children'][1][3]['API_Response']['chapter']['chapter_data']['images']:
                data['pages'].append(dict(
                    slug=None,
                    image=url,
                ))

            return data

        return None
