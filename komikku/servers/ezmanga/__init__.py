# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json
import time

from bs4 import BeautifulSoup

from komikku.consts import DOWNLOAD_MAX_DELAY
from komikku.servers.multi.heancms import extract_info_from_script
from komikku.servers.multi.heancms import HeanCMS
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type
from komikku.utils import get_response_elapsed


class Ezmanga(HeanCMS):
    id = 'ezmanga'
    name = 'EZmanga'
    lang = 'en'

    base_url = 'https://ezmanga.org'
    logo_url = base_url + '/favicon.ico'
    api_url = 'https://api.ezmanga.org'
    api_chapters_url = 'https://vapi.ezmanga.org/api/chapters?postId={0}skip={1}&take={2}&order=desc&search=&userId=undefined'

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
            images = info[1][3]['API_Response']['chapter']['images']

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

    def get_manga_chapters_data(self, serie_id):
        """
        Returns manga chapters list via API
        """
        chapters = []

        def get_page(serie_id, page):
            r = self.session_get(
                self.api_chapters_url.format(serie_id, (page - 1) * 50, page * 50),
                headers={
                    'Referer': f'{self.base_url}/',
                }
            )
            if r.status_code != 200:
                return None, False, None

            data = r.json()
            if not data.get('post'):
                return None, False, None

            more = data['totalChapterCount'] > page * 50

            return data['post']['chapters'], more, get_response_elapsed(r)

        chapters = []
        delay = None
        more = True
        page = 1
        while more:
            if delay:
                time.sleep(delay)

            chapters_page, more, rtime = get_page(serie_id, page)
            if chapters_page:
                for chapter in chapters_page:
                    if chapter['price'] > 0:
                        continue

                    chapters.append(dict(
                        slug=chapter['slug'],
                        title=chapter['title'] or f'Chapter {chapter["number"]}',
                        num=chapter['number'],
                        date=convert_date_string(chapter['createdAt'].split('T')[0], self.date_format) if 'createdAt' in chapter else None,
                    ))
                page += 1
                delay = min(rtime * 2, DOWNLOAD_MAX_DELAY) if rtime else None

            elif chapters_page is None:
                # Failed to retrieve a chapters list page, abort
                break

        return list(reversed(chapters))
