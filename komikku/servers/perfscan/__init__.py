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

            line = line[start:-3].replace('\\"', '"').replace('\\n', '').replace('\\r', '')
            try:
                info = json.loads(line)
            except Exception as e:
                logger.debug(f'ERROR: {line}')
                logger.debug(e)

    return info


class Perfscan(Heancms):
    id = 'perfscan'
    name = 'Perf Scan'
    lang = 'fr'

    base_url = 'https://perf-scan.fr'
    api_url = 'https://api.perf-scan.fr'

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
            status='ongoing',
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        def extract_synopsis(info, synopsis=[]):
            if isinstance(info, list):
                if info[0] == '$':
                    if isinstance(info[3].get('children'), str):
                        # ['$', 'p', None, {'children': 'bla bla bla'}]
                        synopsis.append(info[3]['children'])
                    elif isinstance(info[3]['children'], list):
                        extract_synopsis(info[3]['children'], synopsis)
                else:
                    for sinfo in info:
                        extract_synopsis(sinfo, synopsis)
            elif isinstance(info, str):
                if info != '\\':
                    synopsis.append(info)

            return synopsis

        if info := extract_info_from_script(soup, 'series_slug'):
            info = info[2][3]['children']

            # data['name'] = info[0][3]['children'][3]['children'][3]['children'][1][3]['children'][0][3]['children']
            data['name'] = info[5][3]['children'][3]['children'][3]['children'][3]['post']['title']
            data['cover'] = info[0][3]['children'][3]['children'][3]['children'][0][3]['children'][3]['children'][0][3]['src']

            data['authors'] = info[1][3]['children'][3]['children'][1][3]['children'][2][3]['children'][1][3]['children'][2][3]['children'][2][3]['children'].split(' | ')

            synopsis_info = info[1][3]['children'][3]['children'][1][3]['children'][1][3]['children']
            if synopsis := extract_synopsis(synopsis_info):
                data['synopsis'] = '\n'.join(synopsis)

            seasons = info[3][3]['children'][3]['children'][3]['children'][3]['children'][1]
            for season in reversed(seasons):
                for chapter in reversed(season[3]['season']['chapters']):
                    data['chapters'].append(dict(
                        slug=chapter['chapter_slug'],
                        title=chapter['chapter_name'],
                        date=convert_date_string(chapter['created_at'].split('T')[0], '%Y%m%d'),
                    ))

        return data

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

        if info := extract_info_from_script(soup, 'series_slug'):
            data = dict(
                pages=[],
            )
            pages = info[2][3]['children'][1][3]['children'][0][3]['API_Response']['data']
            for url in pages:
                data['pages'].append(dict(
                    slug=None,
                    image=url,
                ))

            return data

        return None
