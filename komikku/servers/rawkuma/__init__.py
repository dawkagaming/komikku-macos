# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import json
from urllib.parse import parse_qs
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

from komikku.consts import USER_AGENT
from komikku.servers import Server
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type


class Rawkuma(Server):
    id = 'rawkuma'
    name = 'Rawkuma'
    lang = 'ja'
    is_nsfw = True

    base_url = 'https://rawkuma.net'
    logo_url = base_url + '/wp-content/uploads/2025/09/ラークマのサイトアイコンHEADER-96x96.png'
    manga_list_url = base_url + '/wp-admin/admin-ajax.php?action=advanced_search'
    manga_url = base_url + '/manga/{0}/'
    chapters_url = base_url + '/wp-admin/admin-ajax.php?action=chapter_list&manga_id={0}&page=1'
    chapter_url = base_url + '/manga/{0}/{1}/'
    nonce_url = base_url + '/wp-admin/admin-ajax.php?type=search_form&action=get_nonce'

    filters = [
        {
            'key': 'types',
            'type': 'select',
            'name': _('Types'),
            'description': _('Filter by Type'),
            'value_type': 'multiple',
            'options': [
                {'key': 'manga', 'name': _('Manga'), 'default': True},
                {'key': 'manhwa', 'name': _('Manhwa'), 'default': True},
                {'key': 'manhua', 'name': _('Manhua'), 'default': True},
                {'key': 'novel', 'name': _('Novel'), 'default': True},
            ],
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
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = initial_data.copy()
        data.update(dict(
            authors=[],  # not available
            scanlators=[],  # not available
            genres=[],
            status=None,  # not available
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        # Name & cover
        data['name'] = soup.select_one('[itemprop="name"]').text.strip()
        data['cover'] = soup.select_one('[itemprop="image"] img').get('src')

        if elements := soup.select('[itemprop="genre"] span'):
            data['genres'] = [element.text.strip() for element in elements]

        if elements := soup.select('[itemprop="description"] p'):
            data['synopsis'] = [element.text.strip() for element in elements]
        if data['synopsis']:
            data['synopsis'] = '\n\n'.join(data['synopsis'])

        # Chapters
        if manga_id_element := soup.select_one('#chapter-list'):
            url = manga_id_element.get('hx-get').strip()
            manga_id = parse_qs(urlparse(url).query)['manga_id'][0]
        else:
            return None

        chapters = self.get_manga_chapters_data(manga_id)
        if chapters is not None:
            data['chapters'] = list(reversed(chapters))
        else:
            return None

        return data

    def get_manga_chapters_data(self, manga_id):
        r = self.session_get(self.chapters_url.format(manga_id))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        chapters = []
        for element in soup.select('.rounded-md'):
            a_element = element.a

            num = element.get('data-chapter-number')

            title = a_element.select_one('div > div > div > span').text.strip()
            if date_element := element.select_one('time'):
                date = convert_date_string(date_element.get('datetime').split('T')[0], format='%Y-%m-%d')
            else:
                date = None

            chapters.append(dict(
                slug=a_element.get('href').split('/')[-2],
                title=title,
                num=num,
                date=date,
            ))

        return chapters

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(
            self.chapter_url.format(manga_slug, chapter_slug),
            headers={
                'Referer': self.manga_url.format(manga_slug),
            })
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )

        for element in soup.select('section > img'):
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

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['image'].split('/')[-1],
        )

    def get_manga_list(self, title=None, types=None, orderby=None):
        r = self.session_post(
            self.manga_list_url,
            data={
                'nonce': self.get_nonce(),
                'inclusion': 'OR',
                'exclusion': 'OR',
                'page': 1,
                'genre': '[]',
                'genre_exclude': '[]',
                'author': '[]',
                'artist': '[]',
                'project': 0,
                'type': json.dumps(types) or '[]',
                'status': '[]',
                'order': 'desc',
                'orderby': orderby or 'title',
                'query': title or '',
            },
            headers={
                'Referer': f'{self.base_url}/library/',
            }
        )
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.select('div.rounded-lg'):
            a_element = element.a

            slug = a_element.get('href').split('/')[-2]
            name = a_element.img.get('alt')

            results.append(dict(
                slug=slug,
                name=name,
                cover=a_element.img.get('src'),
            ))

        return results

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_nonce(self):
        r = self.session_get(self.nonce_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        if input := soup.select_one('input'):
            return input.get('value')

        return None

    def get_latest_updates(self, types=None):
        return self.get_manga_list(types=types, orderby='updated')

    def get_most_populars(self, types=None):
        return self.get_manga_list(types=types, orderby='popular')

    def search(self, term, types=None):
        return self.get_manga_list(title=term, types=types)
