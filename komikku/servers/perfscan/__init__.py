# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json
import logging

from bs4 import BeautifulSoup

from komikku.servers.multi.heancms import Heancms
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type

logger = logging.getLogger('komikku.servers.perfscan')


def convert_old_slug(slug):
    slug = slug.split('-')
    last_chunk = slug[-1]
    if last_chunk.isdigit() and int(last_chunk) > 10**10:
        return '-'.join(slug[:-1])


def extract_info_from_script(soup, keyword):
    info = None

    for script_element in soup.select('script'):
        script = script_element.string
        if not script or not script.startswith('self.__next_f.push([1,') or keyword not in script:
            continue

        for line in script.split('\n'):
            line = line.strip()
            line = line.replace('self.__next_f.push([1,', '')

            start = 0
            for c in line:
                if c in ('{', '['):
                    break
                start += 1

            line = line[start:-3]
            try:
                info = json.loads(json.loads(f'"{line}"'))
            except Exception as e:
                logger.debug(f'ERROR: {line}')
                logger.debug(e)

    return info


class Perfscan(Heancms):
    id = 'perfscan'
    name = 'Perf Scan'
    lang = 'fr'
    is_nsfw = True

    base_url = 'https://perf-scan.fr'
    api_url = 'https://api.perf-scan.fr'
    api_chapters_url = api_url + '/chapter/query'

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        if new_slug := convert_old_slug(initial_data['slug']):
            initial_data['slug'] = new_slug

        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[self.name, ],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        if info := extract_info_from_script(soup, 'series_slug'):
            info = info[3]['children'][3]['children']

            post = info[2][3]['children'][3]['children'][3]['children'][3]['children'][1][3]['children'][1][3]['children'][3]['post']
            data['name'] = post['title']
            data['cover'] = info[0][3]['children'][3]['children'][1][3]['children'][3]['children'][3]['src']

            # Authors
            for item in info[1][3]['children'][3]['children'][1][3]['children'][1][3]['children']:
                if not isinstance(item[3]['children'][0], list) or item[3]['children'][0][3].get('children') != 'Auteur':
                    continue
                data['authors'] = item[3]['children'][1][3]['children'].split(' | ')
                break

            # Status
            status = info[0][3]['children'][3]['children'][0][3]['children'][1][3]['children'][0][3]['children'].lower()
            if status == 'ongoing':
                data['status'] = 'ongoing'
            elif status == 'completed':
                data['status'] = 'complete'

            # Synopsis
            html = info[0][3]['children'][3]['children'][0][3]['children'][2][3]['children'][3]['dangerouslySetInnerHTML']['__html']
            soup = BeautifulSoup(html, 'lxml')
            data['synopsis'] = soup.text.strip()

            more = True
            page = 1
            while more:
                chapters, more = self.get_manga_chapters_data(post['id'], page)
                for chapter in chapters:
                    data['chapters'].append(dict(
                        slug=chapter['chapter_slug'],
                        title=chapter['chapter_name'],
                        date=convert_date_string(chapter['created_at'].split('T')[0], '%Y%m%d'),
                    ))
                page += 1

        return data

    def get_manga_chapters_data(self, serie_id, page):
        r = self.session_get(
            self.api_chapters_url,
            params=dict(
                page=page,
                perPage=30,
                series_id=serie_id,
            )
        )
        if r.status_code != 200:
            return [], False

        data = r.json()

        return data['data'], data['meta']['current_page'] != data['meta']['last_page']

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

        if info := extract_info_from_script(soup, 'API_Response'):
            data = dict(
                pages=[],
            )
            pages = info[3]['children'][1][3]['children'][0][3]['API_Response']['chapter']['chapter_data']['images']
            for url in pages:
                data['pages'].append(dict(
                    slug=None,
                    image=url,
                ))

            return data

        return None
