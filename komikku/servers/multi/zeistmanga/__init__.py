# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type


class ZeistManga(Server):
    base_url: str

    api_base_url: str = None
    api_search_url: str = None
    api_latest_updates_url: str = None
    api_chapters_url: str = None
    manga_url: str = None
    chapter_url: str = None

    most_popular_selector: str = None
    details_name_selector: str = None
    details_cover_selector: str = None
    details_authors_selector: str = None
    details_type_selector: str = None  # Added in genres
    details_genres_selector: str = None
    details_status_selector: str = None
    details_synopsis_selector: str = None
    chapters_selector: str = None
    chapter_link_selector: str = None
    chapter_title_selector: str = None
    chapter_date_selector: str = None
    pages_selector: str = None

    long_strip_genres = ['Manhua', 'Manhwa']

    def __init__(self):
        if self.api_base_url is None:
            self.api_base_url = self.base_url + '/feeds/posts'
        if self.api_search_url is None:
            self.api_search_url = self.api_base_url + '/default'
        if self.api_latest_updates_url is None:
            self.api_latest_updates_url = self.api_base_url + '/summary/-/Series'
        if self.api_chapters_url is None:
            self.api_chapters_url = self.api_base_url + '/default/-/{0}'
        if self.manga_url is None:
            self.manga_url = self.base_url + '/{0}.html'
        if self.chapter_url is None:
            self.chapter_url = self.base_url + '/{0}.html'

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

        soup = BeautifulSoup(r.text, 'lxml')

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

        data['name'] = soup.select_one(self.details_name_selector).text.strip()
        data['cover'] = soup.select_one(self.details_cover_selector).get('src')

        if element := soup.select_one(self.details_status_selector):
            status = element.text.strip()
            if status == 'Ongoing':
                data['status'] = 'ongoing'
            elif status == 'Completed':
                data['status'] = 'complete'
            elif status in ('Dropped', 'Cancelled'):
                data['status'] = 'suspended'
            elif status == 'Hiatus':
                data['status'] = 'hiatus'

        for element in soup.select(self.details_authors_selector):
            author = element.text.strip()
            if author in data['authors']:
                continue
            data['authors'].append(author)

        if element := soup.select_one(self.details_type_selector):
            data['genres'].append(element.text.strip())

        for element in soup.select(self.details_genres_selector):
            data['genres'].append(element.text.strip())

        data['synopsis'] = soup.select_one(self.details_synopsis_selector).text.strip()

        # Chapters
        data['chapters'] = self.get_manga_chapters_data(soup, data)

        return data

    def get_manga_chapters_data(self, soup, data):
        if script_element := soup.select_one('#clwd script'):
            name = script_element.string.split("'")[1]
        else:
            return []

        r = self.session.get(
            self.api_chapters_url.format(name),
            params={
                'alt': 'json-in-script',
                'start-index': 1,
                'max-results': 150,
            },
            headers={
                'Referer': self.get_manga_url(data['slug'], None),
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        if r.status_code != 200:
            return None

        resp_data = json.loads(r.text.replace('gdata.io.handleScriptLoaded(', '')[:-2])

        chapters = []
        for entry in reversed(resp_data['feed']['entry'][1:]):
            link = None
            for link_ in entry['link']:
                if link_['rel'] == 'alternate':
                    link = link_
                    break

            if not link:
                continue

            chapters.append(dict(
                slug=link['href'].replace(f'{self.base_url}/', '').replace('.html', ''),
                title=entry['title']['$t'].strip(),
                date=convert_date_string(entry['updated']['$t'].split('T')[0], '%Y-%m-%d'),
            ))

        return chapters

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        r = self.session_get(self.chapter_url.format(chapter_slug))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for index, img_element in enumerate(soup.select(self.pages_selector), start=1):
            data['pages'].append(dict(
                slug=None,
                image=img_element.get('src'),
                index=index,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name='{0}.{1}'.format(page['index'], mime_type.split('/')[1]),
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return f'{self.base_url}/{slug}'

    def get_latest_updates(self):
        r = self.session_get(
            self.api_latest_updates_url,
            params={
                'alt': 'json-in-script',
                'start-index': 1,
                'max-results': 150,
            },
            headers={
                'Referer': f'{self.base_url}/',
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        if r.status_code != 200:
            return None

        resp_data = json.loads(r.text.replace('gdata.io.handleScriptLoaded(', '')[:-2])

        results = []
        for item in resp_data['feed']['entry']:
            link = None
            for link_ in item['link']:
                if link_['rel'] == 'alternate':
                    link = link_
                    break

            if not link:
                continue

            results.append(dict(
                slug=link['href'].replace(f'{self.base_url}/', '').replace('.html', ''),
                name=link['title'],
                cover=item['media$thumbnail']['url'],
            ))

        return results

    def get_most_populars(self):
        r = self.session_get(self.base_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select(self.most_popular_selector):
            results.append(dict(
                slug=a_element.get('href').replace(f'{self.base_url}/', '').replace('.html', ''),
                name=a_element.get('title'),
                cover=a_element.img.get('src'),
            ))

        return results

    def search(self, term):
        r = self.session_get(
            self.api_search_url,
            params={
                'alt': 'json',
                'q': f'label:Series "{term}"',  # noqa E231
                'max-results': 25,
            },
            headers={
                'Referer': f'{self.base_url}/',
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()

        results = []
        for item in resp_data['feed'].get('entry', []):
            link = None
            for link_ in item['link']:
                if link_['rel'] == 'alternate':
                    link = link_
                    break

            if not link:
                continue

            results.append(dict(
                slug=link['href'].replace(f'{self.base_url}/', '').replace('.html', ''),
                name=link['title'],
                cover=item['media$thumbnail']['url'],
            ))

        return results
