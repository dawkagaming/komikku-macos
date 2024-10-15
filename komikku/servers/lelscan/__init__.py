# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.utils import get_buffer_mime_type
from komikku.utils import is_number


class Lelscan(Server):
    id = 'lelscan'
    name = 'Lelscan'
    lang = 'fr'
    true_search = False

    base_url = 'https://lelscans.net'
    most_populars_url = base_url + '/lecture-en-ligne-one-piece'
    chapter_url = base_url + '/scan-{0}/{1}'
    page_url = base_url + '/scan-{0}/{1}/{2}'
    cover_url = base_url + '/mangas/{0}/thumb_cover.jpg'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content
        """
        r = self.session_get(initial_data['url'])
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
            status='ongoing',
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = soup.select_one('.outil_lecture h2').text.split('-')[0].strip()
        data['cover'] = self.cover_url.format(data['slug'])

        # Chapters
        for option_element in reversed(soup.select('#header-image select:first-child option')):
            url = option_element.get('value')
            slug = url.split('/')[-1]

            data['chapters'].append(dict(
                slug=slug,
                title='Chapitre {0}'.format(slug),
                num=slug if is_number(slug) else None,
                date=None,
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for a_element in soup.select('#navigation a'):
            text = a_element.text.strip()
            if not text.isdigit():
                continue

            slug = a_element.get('href').split('/')[-1]
            data['pages'].append(dict(
                slug=slug,
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page content
        """
        r = self.session_get(self.page_url.format(manga_slug, chapter_slug, page['slug']))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        path = soup.select_one('#image img').get('src')

        r = self.session_get(self.base_url + path)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=path.split('/')[-1].split('?')[0],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return url

    def get_latest_updates(self):
        """
        Returns hot manga
        """
        r = self.session_get(self.base_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = []
        for a_element in soup.select('#main_hot_ul a.hot_manga_img'):
            url = a_element.get('href')

            slug = url.split('/')[-1]
            for chunk in ('lecture-ligne-', 'lecture-en-ligne-', '.php'):
                slug = slug.replace(chunk, '')

            data.append(dict(
                slug=slug,
                name=a_element.get('title').replace('Scan', '').strip(),
                cover=self.cover_url.format(slug),
                url=url,
            ))

        return data

    def get_most_populars(self):
        r = self.session_get(self.most_populars_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = []
        for option_element in soup.select('#header-image select:last-child option'):
            url = option_element.get('value')

            slug = url.split('/')[-1]
            for chunk in ('lecture-ligne-', 'lecture-en-ligne-', '.php'):
                slug = slug.replace(chunk, '')

            data.append(dict(
                slug=slug,
                name=option_element.text.strip(),
                cover=self.cover_url.format(slug),
                url=url,
            ))

        return data

    def search(self, term=None):
        # This server does not have a search
        # but a search method is needed for `Global Search` in `Explorer`
        # In order not to be offered in `Explorer`, class attribute `true_search` must be set to False

        results = []
        for item in self.get_most_populars():
            if term and term.lower() in item['name'].lower():
                results.append(item)

        return results
