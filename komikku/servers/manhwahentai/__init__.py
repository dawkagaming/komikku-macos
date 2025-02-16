# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json

from bs4 import BeautifulSoup

from komikku.servers.multi.madara import Madara
from komikku.webview import CompleteChallenge
from komikku.utils import get_buffer_mime_type


class Manhwahentai(Madara):
    id = 'manhwahentai'
    name = 'Manhwa Hentai'
    lang = 'en'
    is_nsfw_only = True

    date_format = '%d %B %Y'
    series_name = 'pornhwa'

    base_url = 'https://manhwahentai.to'
    chapters_url = base_url + '/pornhwa/{0}/ajax/chapters/'

    chapters_list_selector = '.manga-post-chapters'
    details_name_selector = '.post-title p.h1'
    details_authors_selector = '.post-tax-wp-manga-artist .post-tags .tag-name'
    details_genres_selector = '.post-tax-wp-manga-category .post-tags .tag-name'
    details_status_selector = None
    details_synopsis_selector = '.summary_content .post-meta:-soup-contains("Description") .post-tag .tag-name'
    results_selector = '.manga'
    result_name_slug_selector = '.post-title a'
    result_cover_selector = '.item-thumb img'

    @CompleteChallenge()
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
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

        data = dict(
            pages=[],
        )

        # Pages images are loaded via javascript
        for script_element in soup.find_all('script'):
            script = script_element.string
            if script is None or script_element.get('id') != 'chapter_preloaded_images':
                continue

            for line in script.split('\n'):
                if 'chapter_preloaded_images' not in line:
                    continue
                line = line.strip()
                json_data = line.split('=')[-1]
                if json_data[-2] == ',':
                    json_data = json_data[:-2] + ']'
                for image in json.loads(json_data):
                    data['pages'].append(dict(
                        slug=None,
                        image=image['src'],
                    ))
                break

        return data
