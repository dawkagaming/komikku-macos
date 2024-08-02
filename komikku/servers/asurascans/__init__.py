# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.multi.madara import Madara
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type


class Asurascans(Server):
    # Probably a modified version of MangaStream theme

    id = 'asurascans'
    name = 'Asura Scans'
    lang = 'en'

    base_url = 'https://asuracomic.net'
    search_url = base_url + '/series'
    manga_url = base_url + '/series/{0}'
    chapter_url = base_url + '/series/{0}/chapter/{1}'

    filters = [
        {
            'key': 'type',
            'type': 'select',
            'name': _('Type'),
            'description': _('Filter by type'),
            'value_type': 'single',
            'default': '',
            'options': [
                {'key': '', 'name': _('All')},
                {'key': 'manga', 'name': _('Manga')},
                {'key': 'manhwa', 'name': _('Manhwa')},
                {'key': 'manhua', 'name': _('Manhua')},
            ],
        },
    ]

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({
                'user-agent': USER_AGENT,
            })

    def check_slug(self, initial_data):
        # A random number is always appended to slug and it changes regularly
        # Try to retrieve new slug
        res = self.search(initial_data['name'], '')
        if not res:
            return None

        for item in res:
            base_slug = '-'.join(initial_data['slug'].split('-')[:-1])
            current_base_slug = '-'.join(item['slug'].split('-')[:-1])
            if current_base_slug in (initial_data['slug'], base_slug) and initial_data['slug'] != item['slug']:
                return item['slug']

        return None

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        if new_slug := self.check_slug(initial_data):
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
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        # Name & cover
        data['name'] = soup.select_one('h3:nth-child(3)').text.strip()
        data['cover'] = soup.select_one('img[alt="poster"]').get('src')

        # Details
        if status_element := soup.select_one('h3:-soup-contains("Status") ~ h3'):
            status = status_element.text.strip().lower()
            if status in ('ongoing', 'season end'):
                data['status'] = 'ongoing'
            elif status == 'completed':
                data['status'] = 'complete'
            elif status == 'dropped':
                data['status'] = 'suspended'
            elif status == 'hiatus':
                data['status'] = 'hiatus'

        if author_element := soup.select_one('h3:-soup-contains("Author") ~ h3'):
            data['authors'].append(author_element.text.strip())
        if author_element := soup.select_one('h3:-soup-contains("Artist") ~ h3'):
            data['authors'].append(author_element.text.strip())

        for element in soup.select('h3:-soup-contains("Genre") ~ div button'):
            data['genres'].append(element.text.strip())

        if synopsis_element := soup.select_one('h3:-soup-contains("Synopsis") ~ span'):
            data['synopsis'] = synopsis_element.text.strip()

        # Chapters
        data['chapters'] = self.get_manga_chapters_data(soup)

        return data

    def get_manga_chapters_data(self, soup):
        chapters = []

        for element in reversed(soup.select('.scrollbar-thin > div')):
            a_element = element.select_one('h3:first-child a')
            if date_element := element.select_one('h3:last-child'):
                date = convert_date_string(date_element.text.strip())
            else:
                date = None

            chapters.append(dict(
                slug=a_element.get('href').split('/')[-1],
                title=a_element.text.strip(),
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

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for img_element in soup.select('img[alt="chapter"]'):
            image = img_element.get('src')
            data['pages'].append(dict(
                slug=None,
                image=image,
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

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_manga_list(self, term='', type=None, orderby=None):
        r = self.session_get(
            self.search_url,
            params=dict(
                page=1,
                name=term,
                genres='',
                status=-1,
                types=-1,
                order=orderby or 'asc',
            ),
            headers={
                'referer': self.base_url,
            }
        )
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select('.grid.grid-cols-2 > a'):
            cover_element = a_element.select_one('img.object-cover')

            results.append(dict(
                slug=a_element.get('href').split('/')[-1],
                name=a_element.select_one('span.block.font-bold').text.strip(),
                cover=cover_element.get('src') if cover_element else None,
            ))

        return results

    def get_latest_updates(self, type):
        return self.get_manga_list(type=type, orderby='latest')

    def get_most_populars(self, type):
        return self.get_manga_list(type=type, orderby='rating')

    def search(self, term, type):
        return self.get_manga_list(term=term, type=type)


class Asurascans_tr(Madara):
    id = 'asurascans_tr'
    name = 'Armoni Scans (Asura Scans)'
    lang = 'tr'

    date_format = '%d %B %Y'

    base_url = 'https://asurascans.com.tr'
