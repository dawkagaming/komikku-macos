# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# Supported servers:
# Anteiku Scans [FR]
# ED Scanlation [FR]
# EZmanga [EN]
# Kewn Scans [EN]
# Starbound Scans [FR]

import logging

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type

logger = logging.getLogger(__name__)


class Keyoapp(Server):
    base_url: str
    search_url: str = None
    latest_updates_url: str = None
    most_populars_url: str = None
    manga_url: str = None
    chapter_url: str = None
    media_url: str = None

    long_strip_genres = ['Manhua', 'Manhwa']

    def __init__(self):
        if self.search_url is None:
            self.search_url = self.base_url + '/series'
        if self.latest_updates_url is None:
            self.latest_updates_url = self.base_url + '/latest/'
        if self.most_populars_url is None:
            self.most_populars_url = self.base_url
        if self.manga_url is None:
            self.manga_url = self.base_url + '/series/{0}/'
        if self.chapter_url is None:
            self.chapter_url = self.base_url + '/chapter/{0}/'
        if self.media_url is None:
            self.media_url = 'https://cdn.keyoapp.com'

        if self.session is None and not self.has_cf:
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
            authors=[],
            scanlators=[self.name, ],
            genres=[],
            status='ongoing',
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = soup.find('h1').text.strip()

        if element := soup.select_one('div[style*="--photoURL"]'):
            url = element.get('style').split('url')[-1][1:-1]
            data['cover'] = url
        if element := soup.select_one('div[style*="--posterurl"]'):
            url = element.get('style').split('url')[-1][1:-1]
            data['cover'] = url

        # Details
        for element in soup.select('h1 ~ div > div, h1 ~ div > a'):
            title = element.get('title')

            if title == 'Status':
                status = element.span.text.strip().lower()
                if status == 'ongoing':
                    data['status'] = 'ongoing'
                elif status == 'completed':
                    data['status'] = 'complete'
                elif status == 'pause':
                    data['status'] = 'hiatus'
                elif status == 'dropped':
                    data['status'] = 'suspended'

            elif title in ('Author', 'Artist'):
                author = element.span.text.strip()
                if author not in data['authors']:
                    data['authors'].append(author)

            elif title in ('Last Updated At', 'View Count'):
                pass

            else:
                genre = element.span.text.strip().capitalize()
                data['genres'].append(genre)

        if element := soup.select_one('p[style="white-space: pre-wrap"]'):
            data['synopsis'] = element.text.strip()

        # Chapters
        data['chapters'] = self.get_manga_chapters_data(soup)

        return data

    def get_manga_chapters_data(self, soup):
        """
        Returns manga chapters list
        """
        chapters = []
        for element in reversed(soup.select('#chapters a')):
            chapters.append(dict(
                slug=element.get('href').split('/')[-2],
                title=element.get('title'),
                date=convert_date_string(element.get('d')),
            ))

        return chapters

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content
        """
        r = self.session_get(
            self.chapter_url.format(chapter_slug),
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
        for element in soup.select('#pages img'):
            url = element.get('data-src')
            if not url.startswith(self.media_url):
                continue

            data['pages'].append(dict(
                slug=None,
                image=url,
                index=int(element.get('count')),
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page['image'],
            headers={
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
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
            name='{0:03d}.{1}'.format(page['index'], mime_type.split('/')[-1]),
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_latest_updates(self):
        """
        Returns latest updates
        """
        r = self.session_get(self.latest_updates_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select('.latest-poster > a'):
            results.append(dict(
                slug=a_element.get('href').split('/')[-2],
                name=a_element.get('title'),
                cover=a_element.get('style').split('url')[-1][1:-1],
            ))

        return results

    def get_most_populars(self):
        """
        Returns most popular manga
        """
        r = self.session_get(self.most_populars_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select('.flex-col .grid > .group.border > a'):
            results.append(dict(
                slug=a_element.get('href').split('/')[-2],
                name=a_element.get('title'),
                cover=a_element.get('style').split('url')[-1][1:-1].replace('w=480', 'w=240').replace('w=80', 'w=240'),
            ))

        return results

    def search(self, term):
        r = self.session_get(
            self.search_url,
            params={
                'q': term,
            },
            headers={
                'Referer': f'{self.base_url}/',
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.select('#searched_series_page button'):
            name = element.get('title')
            if term and term.lower() not in name.lower():
                continue

            results.append(dict(
                slug=element.get('id'),
                name=name,
                cover=element.select_one('.bg-cover').get('style').split('url')[-1][1:-1],
            ))

        return results
