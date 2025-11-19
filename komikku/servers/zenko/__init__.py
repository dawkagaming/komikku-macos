# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import datetime
from gettext import gettext as _
import time

import requests

from komikku.consts import DOWNLOAD_MAX_DELAY
from komikku.consts import USER_AGENT
from komikku.servers import Server
from komikku.utils import get_buffer_mime_type
from komikku.utils import get_response_elapsed
from komikku.utils import is_number

SEARCH_RESULTS_PAGES = 5


class Zenko(Server):
    id = 'zenko'
    name = 'Zenko'
    lang = 'uk'

    is_nsfw = True

    base_url = 'https://zenko.online'
    logo_url = base_url + '/favicon.ico'

    manga_url = base_url + '/titles/{0}'
    chapter_url = base_url + '/titles/{0}/{1}'
    image_url = 'https://zenko.b-cdn.net/{0}?optimizer=image&width=560&quality=70&height=auto'

    api_url = 'https://zenko-api.onrender.com'
    api_search_url = api_url + '/titles'
    api_manga_url = api_url + '/titles/{0}'
    api_chapters_url = api_url + '/titles/{0}/chapters'
    api_chapter_url = api_url + '/chapters/{0}'

    filters = [
        {
            'key': 'age_limit',
            'type': 'select',
            'name': _('Age Restriction'),
            'description': _('Filter by Age Restrictions'),
            'value_type': 'multiple',
            'options': [
                {'key': '0', 'name': '0', 'default': True},
                {'key': '16', 'name': '16+', 'default': False},
                {'key': '18', 'name': '18+', 'default': False},
            ]
        },
        {
            'key': 'statuses',
            'type': 'select',
            'name': _('Status'),
            'description': _('Filter by Statuses'),
            'value_type': 'multiple',
            'options': [
                {'key': 'ONGOING', 'name': _('Ongoing'), 'default': False},
                {'key': 'FINISHED', 'name': _('Completed'), 'default': False},
                {'key': 'PAUSED', 'name': _('Hiatus'), 'default': False},
            ]
        },
        {
            'key': 'types',
            'type': 'select',
            'name': _('Type'),
            'description': _('Filter by Types'),
            'value_type': 'multiple',
            'options': [
                {'key': 'MANGA_UA', 'name': _('Manga UA'), 'default': False},
                {'key': 'MANGA', 'name': _('Manga'), 'default': False},
                {'key': 'MANHVA', 'name': _('Manhwa'), 'default': False},
                {'key': 'MANHUA', 'name': _('Manhua'), 'default': False},
                {'key': 'WESTERN_COMICS', 'name': _('Western Comic'), 'default': False},
                {'key': 'COMICS', 'name': _('Comic'), 'default': False},
                {'key': 'RANOBE', 'name': _('Light Novel'), 'default': False},
                {'key': 'OTHER', 'name': _('Other'), 'default': False},
            ],
        },
    ]

    headers = {
        'User-Agent': USER_AGENT,
    }

    long_strip_genres = [
        'MANHUA',
        'MANHVA',
    ]

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = self.headers

    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.api_manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        resp_data = r.json()

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = resp_data['engName'] if resp_data.get('engName') else resp_data['name']
        if cover_id := resp_data.get('coverImg'):
            data['cover'] = self.image_url.format(cover_id)

        # Details
        if resp_data['status'] == 'FINISHED':
            data['status'] = 'complete'
        elif resp_data['status'] == 'ONGOING':
            data['status'] = 'ongoing'
        elif resp_data['status'] == 'PAUSED':
            data['status'] = 'hiatus'

        if genres := resp_data.get('genres'):
            for genre in genres:
                data['genres'].append(genre['name'])

        if tags := resp_data.get('tags'):
            for tag in tags:
                if not tag['isVerified'] or tag['name'] in data['genres']:
                    continue
                data['genres'].append(tag['name'])

        if category := resp_data.get('category'):
            data['genres'].append(category)

        if writers := resp_data['writers']:
            for writer in writers:
                data['authors'].append(writer['name'])

        if painters := resp_data['painters']:
            for painter in painters:
                if painter['name'] in data['authors']:
                    continue
                data['authors'].append(painter['name'])

        if teams := resp_data.get('teams'):
            for team in teams:
                data['scanlators'].append(team['name'])

        if synopsis := resp_data.get('description'):
            data['synopsis'] = f'{resp_data["name"]}\n\n{synopsis}'

        # Chapters
        r = self.session_get(
            self.api_chapters_url.format(data['slug']),
            headers={
                'Referer': self.manga_url.format(data['slug']),
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()

        for chapter in reversed(resp_data):
            num_volume = None
            num = None
            name = None

            parts = chapter['name'].split('@#%&;№%#&**#!@')
            size = len(parts)

            if size == 3:
                num_volume, num, name = parts
            elif size == 2:
                num_volume, num = parts
            elif size == 1:
                name = parts[0]

            title = []
            if num_volume:
                title.append(f'Том {num_volume}')
            if num:
                title.append(f'Розділ {num}')
            if name:
                title.append(name)

            ts = chapter['updatedAt'] if chapter.get('updatedAt') else chapter['createdAt']
            data['chapters'].append(dict(
                slug=chapter['id'],
                title=' '.join(title),
                num=num if is_number(num) else None,
                num_volume=num_volume if is_number(num_volume) else None,
                scanlators=[chapter['publisher']['name']] if chapter.get('publisher') else None,
                date=datetime.datetime.fromtimestamp(ts).date(),
            ))

        def sort_func(c):
            if c['num_volume'] or c['num']:
                return '{0:03d}{1:05.1f}'.format(
                    int(c['num_volume']) if c['num_volume'] else 0,
                    float(c['num']) if c['num'] else 0
                )

            return c['slug']

        data['chapters'] = sorted(data['chapters'], key=sort_func)

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data from API

        Currently, only pages are expected.
        """
        r = self.session_get(
            self.api_chapter_url.format(chapter_slug),
            headers={
                'Referer': self.chapter_url.format(manga_slug, chapter_slug),
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()

        data = dict(
            pages=[],
        )
        for page in resp_data['pages']:
            data['pages'].append(dict(
                slug=page['content'],
                image=None,
                index=page['order'] + 1,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(self.image_url.format(page['slug']))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name='{0:03d}.{1}'.format(page['index'], mime_type.split('/')[-1]),
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_manga_list(self, term=None, age_limit=None, statuses=None, types=None, orderby=None):
        def get_page(page):
            params = {
                'limit': 15,
                'offset': (page - 1) * 15,
                'order': 'DESC',
                'ageLimit': ','.join(age_limit) if age_limit else 0,
                'releaseYearFrom': 1980,
                'releaseYearTo': datetime.date.today().year,
            }
            if term:
                params['name'] = term

            if statuses:
                params['status'] = ','.join(statuses)
            if types:
                params['categories'] = ','.join(types)

            if orderby == 'popular':
                params['sortBy'] = 'viewsCount'
            elif orderby == 'latest':
                params['sortBy'] = 'lastChapterCreatedAt'
            else:
                params['sortBy'] = 'createdAt'

            r = self.session_get(
                self.api_search_url,
                params=params,
                headers={
                    'Referer': f'{self.base_url}/',
                }
            )
            if r.status_code != 200:
                return [], False, None

            resp_data = r.json()

            more = page < resp_data['meta']['totalPages'] and page < SEARCH_RESULTS_PAGES

            return resp_data['data'], more, get_response_elapsed(r)

        results = []
        delay = None
        more = True
        page = 1
        while more:
            if delay:
                time.sleep(delay)

            items, more, rtime = get_page(page)
            for item in items:
                results.append(dict(
                    slug=item['id'],
                    name=item['engName'] if item.get('engName') else item['name'],
                    cover=self.image_url.format(item['coverImg']),
                ))

            delay = min(rtime * 4, DOWNLOAD_MAX_DELAY) if rtime else None
            page += 1

        return results

    def get_latest_updates(self, age_limit=None, statuses=None, types=None):
        return self.get_manga_list(age_limit=age_limit, statuses=statuses, types=types, orderby='latest')

    def get_most_populars(self, age_limit=None, statuses=None, types=None):
        return self.get_manga_list(age_limit=age_limit, statuses=statuses, types=types, orderby='popular')

    def search(self, term, age_limit=None, statuses=None, types=None):
        return self.get_manga_list(term=term, age_limit=age_limit, statuses=statuses, types=types)
