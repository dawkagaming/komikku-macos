# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from functools import wraps
from gettext import gettext as _
import json
import re

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_soup_element_inner_text
from komikku.utils import get_buffer_mime_type

RE_CHAPTER_PAGES = r'.*pages\s+=\s+([a-zA-Z0-9":,-_.\[\]{}]+);.*'
RE_CHAPTER_PAGES_CDN = r'.*var\s+cdn\s+=\s+"([a-z1-9]+[^"])";.*'


def get_data(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        server = args[0]
        if server.csrf_token:
            return func(*args, **kwargs)

        r = server.session_get(server.base_url)
        if r.status_code != 200:
            return func(*args, **kwargs)

        soup = BeautifulSoup(r.text, 'lxml')
        server.csrf_token = soup.select_one('meta[name="csrf-token"]')['content']

        return func(*args, **kwargs)

    return wrapper


class Mangamana(Server):
    id = 'mangamana'
    name = 'Manga Mana'
    lang = 'fr'

    base_url = 'https://www.manga-mana.com'
    search_url = base_url + '/search-live'
    manga_list_url = base_url + '/liste-mangas'
    manga_url = base_url + '/m/{0}'
    chapter_url = base_url + '/m/{0}/{1}'
    image_url = 'https://{0}.manga-mana.com/uploads/manga/{1}/chapters_fr/{2}/{3}?{4}'
    cover_url = 'https://cdn.manga-mana.com/uploads/manga/{0}/cover/cover_thumb.jpg'

    filters = [
        {
            'key': 'status',
            'type': 'select',
            'name': _('Status'),
            'description': _('Status'),
            'value_type': 'single',
            'default': None,
            'options': [
                {'key': '1', 'name': _('Ongoing')},
                {'key': '2', 'name': _('Complete')},
                {'key': '3', 'name': _('Suspended')},
            ]
        },
    ]

    csrf_token = None

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=self.cover_url.format(data['slug']),
        ))

        soup = BeautifulSoup(r.text, 'lxml')

        data['name'] = soup.select_one('h1').text.strip()

        # Details
        if element := soup.select_one('.show_details :-soup-contains("Statut") > span'):
            status = element.text.strip()
            if status == 'En Cours':
                data['status'] = 'ongoing'
            elif status == 'Terminé':
                data['status'] = 'complete'
            elif status == 'Abandonné':
                data['status'] = 'suspended'

        for element in soup.select('.show_details span[itemprop="author"] > a'):
            author = element.text.strip()
            data['authors'].append(author)
        for element in soup.select('.show_details span[itemprop="illustrator"] > a'):
            artist = element.text.strip()
            if artist not in data['authors']:
                data['authors'].append(artist)
        for element in soup.select('.show_details span[itemprop="translator"] > span'):
            scanlator = element.text.strip()
            data['scanlators'].append(scanlator)

        for element in soup.select('a[itemprop="genre"]'):
            genre = element.text.strip()
            data['genres'].append(genre)

        if element := soup.select_one('dd[itemprop="description"]'):
            data['synopsis'] = get_soup_element_inner_text(element, recursive=False)
            if more_element := element.select_one('#more'):
                data['synopsis'] += ' ' + more_element.text.strip()

        # Chapters
        for a_element in reversed(soup.select('.chapter_link')):
            data['chapters'].append(dict(
                slug=a_element.get('href').split('/')[-1],
                title=get_soup_element_inner_text(a_element.div.div, recursive=False),
                date=convert_date_string(a_element.div.div.div.text.strip(), languages=['fr']),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chpater HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        cdn = None
        pages = None
        for script_element in soup.find_all('script'):
            script = script_element.string
            if not script or 'var pages' not in script:
                continue

            for line in script.split('\n'):
                if matches := re.search(RE_CHAPTER_PAGES, line):
                    pages = json.loads(matches.group(1))
                if matches := re.search(RE_CHAPTER_PAGES_CDN, line):
                    cdn = matches.group(1)

            if cdn and pages:
                break

        if not cdn or not pages:
            return None

        data = dict(
            pages=[],
        )
        for page in pages:
            data['pages'].append(dict(
                slug=None,
                image=self.image_url.format(cdn, manga_slug, chapter_slug, page['image'], page['version']),
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page['image'],
            headers={
                'Referer': f'{self.base_url}/',
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

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    @get_data
    def get_manga_list(self, orderby, status):
        r = self.session_post(
            self.manga_list_url,
            data={
                'category': '',
                'status': status or '',
                'sort_by': orderby,
                'sort_dir': 'desc',
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': self.manga_list_url,
                'X-CSRF-TOKEN': self.csrf_token,
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        if r.status_code != 200:
            return None

        data = r.json()
        if not data['success']:
            return None

        soup = BeautifulSoup(data['html'], 'lxml')

        result = []
        for element in soup.select('.mangalist_item'):
            a_element = element.select_one('div:nth-child(2) > div > a')
            slug = a_element.get('href').split('/')[-1]
            if not slug:
                continue

            result.append(dict(
                name=a_element.text.strip(),
                slug=slug,
                cover=element.div.img.get('data-src').strip(),
            ))

        return result

    def get_latest_updates(self, status=None):
        return self.get_manga_list('updated_at', status)

    def get_most_populars(self, status=None):
        return self.get_manga_list('score', status)

    @get_data
    def search(self, term, status=None):
        r = self.session_get(
            self.search_url,
            params={
                'q': term,
            },
            headers={
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': f'{self.base_url}/',
                'X-CSRF-TOKEN': self.csrf_token,
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        if r.status_code != 200:
            return None

        result = []
        for item in r.json():
            result.append(dict(
                name=item['name'],
                slug=item['slug'],
                cover=self.cover_url.format(item['slug']),
            ))

        return result
