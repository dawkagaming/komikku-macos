# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import datetime
from gettext import gettext as _
import json
from urllib.parse import unquote

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.utils import get_buffer_mime_type
from komikku.utils import is_number


class Flamescans(Server):
    id = 'flamescans'
    name = 'Flame Comics (Flame Scans)'
    lang = 'en'

    base_url = 'https://flamecomics.xyz'
    search_url = base_url + '/browse'
    manga_url = base_url + '/series/{0}'
    chapter_url = base_url + '/series/{0}/{1}'
    cover_url = base_url + '/_next/image?url=https%3A%2F%2Fcdn.flamecomics.xyz%2Fseries%2F{0}%2F{1}&w=256&q=75'

    long_strip_genres = ['Manhua', 'Manhwa']

    filters = [
        {
            'key': 'types',
            'type': 'select',
            'name': _('Types'),
            'description': _('Filter by Types'),
            'value_type': 'multiple',
            'options': [
                {'key': 'Manga', 'name': _('Manga'), 'default': False},
                {'key': 'Manhwa', 'name': _('Manhwa'), 'default': False},
                {'key': 'Manhua', 'name': _('Manhua'), 'default': False},
            ],
        },
        {
            'key': 'statuses',
            'type': 'select',
            'name': _('Statuses'),
            'description': _('Filter by Statuses'),
            'value_type': 'multiple',
            'options': [
                {'key': 'Ongoing', 'name': _('Ongoing'), 'default': False},
                {'key': 'Completed', 'name': _('Completed'), 'default': False},
                {'key': 'Hiatus', 'name': _('Hiatus'), 'default': False},
                {'key': 'Dropped', 'name': _('Dropped'), 'default': False},
                {'key': 'Cancelled', 'name': _('Canceled'), 'default': False},
            ]
        },
    ]

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],  # not available
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        soup = BeautifulSoup(r.text, 'lxml')

        found = False
        for script_element in soup.select('script'):
            script = script_element.string
            if not script or script_element.get('id') != '__NEXT_DATA__':
                continue

            try:
                serie_data = json.loads(script)['props']['pageProps']['series']
            except Exception:
                break

            found = True
            data['name'] = serie_data['title']
            data['cover'] = self.cover_url.format(data['slug'], serie_data['cover'])

            # Details
            if serie_data.get('author'):
                data['authors'].append(serie_data['author'])
            if serie_data.get('artist'):
                data['authors'].append(serie_data['artist'])

            if serie_data.get('tags'):
                data['genres'] = json.loads(serie_data['tags'])
            if serie_data.get('type'):
                data['genres'].append(serie_data['type'])

            if serie_data['status'] == 'Ongoing':
                data['status'] = 'ongoing'
            elif serie_data['status'] == 'Completed':
                data['status'] = 'complete'
            elif serie_data['status'] in ('Dropped', 'Cancelled'):
                data['status'] = 'suspended'
            elif serie_data['status'] == 'Hiatus':
                data['status'] = 'hiatus'
            else:
                data['genres'].append(serie_data['status'])

            if serie_data.get('description'):
                data['synopsis'] = serie_data['description']

            # Chapters
            chapters_data = json.loads(script)['props']['pageProps']['chapters']
            for chapter in reversed(chapters_data):
                if is_number(chapter['chapter']):
                    if float(chapter['chapter']) == int(float(chapter['chapter'])):
                        num = int(float(chapter['chapter']))
                    else:
                        num = float(chapter['chapter'])
                    title = f'Chapter {num}'
                else:
                    title = chapter['chapter']

                data['chapters'].append(dict(
                    slug=chapter['token'],
                    title=title,
                    num=num if is_number(num) else None,
                    date=datetime.date.fromtimestamp(chapter['unix_timestamp']),
                ))

        if not found:
            return None

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        r = self.session_get(
            self.chapter_url.format(manga_slug, chapter_slug),
        )
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for element in soup.select('img[fit="contain"]'):
            data['pages'].append(dict(
                slug=None,
                image=element.get('src'),
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page['image'],
            headers={
                'Referer': self.chapter_url.format(manga_slug, chapter_slug),
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        name = unquote(page['image'].split('url=')[-1]).split('?')[0].split('/')[-1]

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=name,
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_manga_list(self, term=None, orderby=None, types=None, statuses=None):
        if term:
            r = self.session_get(self.search_url)
        else:
            r = self.session_get(self.base_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        found = False
        results = []
        for script_element in soup.select('script'):
            script = script_element.string
            if not script or script_element.get('id') != '__NEXT_DATA__':
                continue

            try:
                data = json.loads(script)
            except Exception:
                break

            found = True
            if term:
                series = data['props']['pageProps']['series']
            elif orderby == 'popular':
                series = data['props']['pageProps']['popularEntries']['blocks'][0]['series']
            elif orderby == 'latest':
                series = data['props']['pageProps']['latestEntries']['blocks'][0]['series']

            for serie in series:
                if term and term.lower() not in serie['title'].lower():
                    continue

                if types and serie['type'] not in types:
                    continue

                if statuses and serie['status'] not in statuses:
                    continue

                results.append({
                    'slug': serie['series_id'],
                    'name': serie['title'],
                    'cover': self.cover_url.format(serie['series_id'], serie['cover']),
                })

        if not found:
            return None

        return results

    def get_latest_updates(self, types=None, statuses=None):
        return self.get_manga_list(orderby='latest', statuses=statuses, types=types)

    def get_most_populars(self, types=None, statuses=None):
        return self.get_manga_list(orderby='popular', statuses=statuses, types=types)

    def search(self, term='', types=None, statuses=None):
        return self.get_manga_list(term=term, statuses=statuses, types=types)
