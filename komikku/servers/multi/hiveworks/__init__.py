# Copyright (C) 2025-2025 Seth Falco
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Seth Falco <seth@falco.fun>

import json

from bs4 import BeautifulSoup
import requests
import textwrap

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type


class Hiveworks(Server):
    lang = 'en'
    true_search = False

    manga_url = None
    chapter_url = None
    image_url = None
    cover_url = None

    def __init__(self):
        if self.manga_url is None:
            self.manga_url = self.base_url + '/comic/archive'
        if self.chapter_url is None:
            self.chapter_url = self.base_url + '/comic/{0}'
        if self.image_url is None:
            self.image_url = self.base_url + '/comics/{0}'

        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """Returns manga data by scraping manga HTML page content"""
        r = self.session_get(self.manga_url)
        if r is None:
            return None

        mime_type = get_buffer_mime_type(r.content)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')
        metadata = self.get_metadata(soup)

        data = initial_data.copy()
        data.update(dict(
            authors=metadata['authors'],
            scanlators=[],
            genres=[],
            status='ongoing',
            synopsis=metadata['synopsis'],
            chapters=[],
            server_id=self.id,
            cover=self.cover_url,
        ))

        for option_element in soup.find('select', attrs={'name': 'comic'}).find_all('option')[1:]:
            slug = option_element.get('value').split('/')[-1]
            date_str, title = option_element.text.split(' - ', 1)

            data['chapters'].append(dict(
                slug=slug,
                date=convert_date_string(date_str, format='%B %d, %Y', languages=[self.lang]),
                title=title,
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(chapter_slug))
        if r is None:
            return None

        mime_type = get_buffer_mime_type(r.content)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')
        img = soup.find('img', id='cc-comic')

        return dict(
            pages=[
                dict(
                    slug=None,
                    image=img.get('src').split('/')[-1],
                ),
                dict(
                    slug=None,
                    image=None,
                    text=img.get('title'),
                )
            ]
        )

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """Returns chapter page scan (image) content"""
        if page.get('image'):
            r = self.session_get(self.image_url.format(page['image']))
            name = page['image']
        else:
            r = self.session_get(
                'https://fakeimg.pl/1500x2126/ffffff/000000/',
                params=dict(
                    text='\n'.join(textwrap.wrap(page['text'], 25)),
                    font_size=64,
                    font='museo'
                )
            )
            name = '{0}-alt-text.png'.format(chapter_slug)

        if r is None or r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=name,
        )

    def get_manga_url(self, slug, url):
        """Returns manga absolute URL"""
        return self.base_url

    def get_most_populars(self):
        return [dict(
            slug='',
            name=self.name,
            cover=self.cover_url,
        )]

    def search(self, term=None):
        """
        This server does not have a search but a search method is needed for
        `Global Search` in `Explorer`. In order not to be offered in `Explorer`,
        class attribute `true_search` must be set to False.
        """
        results = []
        for item in self.get_most_populars():
            if term and term.lower() in item['name'].lower():
                results.append(item)

        return results

    def get_metadata(self, soup: BeautifulSoup):
        linked_data_str = soup.find('script', attrs={'type': 'application/ld+json'}).contents[0]
        linked_data = json.loads(linked_data_str)
        return {
            'authors': [linked_data['author'], ],
            'synopsis': linked_data['about'],
        }
