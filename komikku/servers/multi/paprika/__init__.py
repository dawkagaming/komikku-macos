# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# Supported servers:
# Mangareadercc [EN]

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.utils import get_buffer_mime_type


class Paprika(Server):
    base_url: str
    search_url: str = None
    latest_updates_url: str = None
    most_populars_url: str = None
    manga_url: str = None
    chapter_url: str = None

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': USER_AGENT})

        if self.search_url is None:
            self.search_url = self.base_url + '/search'
        if self.latest_updates_url is None:
            self.latest_updates_url = self.base_url + '/latest-manga'
        if self.most_populars_url is None:
            self.most_populars_url = self.base_url + '/popular-manga'
        if self.manga_url is None:
            self.manga_url = self.base_url + '/manga/{0}'
        if self.chapter_url is None:
            self.chapter_url = self.base_url + '/chapter/{0}'

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

        data['name'] = soup.select_one('h1').text.strip()
        data['cover'] = soup.select_one('.imgdesc img').get('src')

        if element := soup.select_one('.listinfo li:-soup-contains("Author")'):
            element.b.extract()
            author = element.text[1:].strip()
            data['authors'].append(author)

        if element := soup.select_one('.listinfo li:-soup-contains("Status")'):
            element.b.extract()
            status = element.text[1:].strip()
            if status == 'Ongoing':
                data['status'] = 'ongoing'
            elif status == 'Completed':
                data['status'] = 'complete'

        if element := soup.select_one('.listinfo li:-soup-contains("Genres")'):
            element.b.extract()
            genres = element.text[1:].strip()
            for genre in genres.split(','):
                data['genres'].append(genre.strip())

        if element := soup.select_one('#noidungm'):
            data['synopsis'] = element.text.strip()

        # Chapters
        for a_element in reversed(soup.select('.cl li a')):
            title = a_element.text.strip()
            num = title.split(' ')[-1]

            data['chapters'].append(dict(
                slug=a_element.get('href').split('/')[-1],
                title=title,
                num=num if num.isdigit() else None,
                date=None,
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        r = self.session_get(self.chapter_url.format(chapter_slug))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for url in soup.select_one('#arraydata').text.split(','):
            data['pages'].append(dict(
                slug=None,
                image=url.strip(),
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page['image'],
            headers={
                'Referer': self.chapter_url.format(chapter_slug),
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

    def get_latest_updates(self):
        r = self.session_get(self.latest_updates_url)
        if r.status_code != 200:
            return None

        return self.parse_manga_list(r.text)

    def get_most_populars(self):
        r = self.session_get(self.most_populars_url)
        if r.status_code != 200:
            return None

        return self.parse_manga_list(r.text)

    def parse_manga_list(self, html):
        soup = BeautifulSoup(html, 'lxml')

        results = []
        for element in soup.select('.anipost'):
            a_element = element.select_one('.left a')
            results.append(dict(
                slug=a_element.get('href').split('/')[-1],
                name=a_element.select_one('h3').text.strip(),
                cover=element.select_one('.thumb img').get('src'),
            ))

        return results

    def search(self, term):
        r = self.session_get(
            self.search_url,
            params={
                's': term,
                'post_type': 'manga',
            },
            headers={
                'Referer': self.base_url,
            }
        )
        if r.status_code != 200:
            return None

        return self.parse_manga_list(r.text)
