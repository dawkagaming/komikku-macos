# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import time
from urllib.parse import parse_qs
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

from komikku.servers import DOWNLOAD_MAX_DELAY
from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type
from komikku.utils import get_response_elapsed
from komikku.utils import is_number

SEARCH_MAX_PAGES = 2


class Mangademon(Server):
    id = 'mangademon'
    name = 'Manga Demon'
    lang = 'en'

    base_url = 'https://demonicscans.org'
    search_url = base_url + '/search.php'
    latest_updates_url = base_url + '/lastupdates.php'
    most_populars_url = base_url + '/advanced.php'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/chaptered.php?manga={0}&chapter={1}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = {
                'User-Agent': USER_AGENT
            }

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        _id, slug = initial_data['slug'].split('_')
        r = self.session_get(self.manga_url.format(slug))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        )

        first_chapter_url = soup.select_one('#read-first').get('href')
        qs = parse_qs(urlparse(first_chapter_url).query)
        id = qs['manga'][0]

        data['slug'] = f'{id}_{slug}'
        data['name'] = soup.select_one('title').text.strip()
        if element := soup.select_one('#manga-page img'):
            data['cover'] = element.get('src')

        # Details
        for element in soup.select('.genres-list li'):
            genre = element.text.strip()
            if genre not in data['genres']:
                data['genres'].append(genre)

        if element := soup.select_one('#manga-info-stats :-soup-contains("Author") li:last-child'):
            data['authors'].append(element.text.strip())

        if element := soup.select_one('#manga-info-stats :-soup-contains("Status") li:last-child'):
            status = element.text.strip()
            if status == 'Ongoing':
                data['status'] = 'ongoing'
            elif status == 'Completed':
                data['status'] = 'complete'

        # Synopsis
        if element := soup.select_one('#manga-info-rightColumn .white-font'):
            data['synopsis'] = element.text.strip()

        # Chapters
        chapters_slugs = []
        for element in reversed(soup.select('#chapters-list li')):
            url = element.a.get('href')
            qs = parse_qs(urlparse(url).query)
            slug = qs['chapter'][0]
            if slug in chapters_slugs:
                continue

            data['chapters'].append(dict(
                slug=slug,
                title=element.a.get('title').strip(),
                num=slug if is_number(slug) else None,
                date=convert_date_string(element.a.span.text.strip(), format='%Y-%m-%d'),
            ))
            chapters_slugs.append(slug)

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        manga_id = manga_slug.split('_')[0]
        r = self.session_get(self.chapter_url.format(manga_id, chapter_slug))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for img_element in soup.select('div > .imgholder'):
            data['pages'].append(dict(
                slug=None,
                image=img_element.get('src'),
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        manga_id = manga_slug.split('_')[0]
        r = self.session_get(
            page['image'],
            headers={
                'Referer': self.chapter_url.format(manga_id, chapter_slug),
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
        _id, slug = slug.split('_')
        return self.manga_url.format(slug)

    def get_latest_updates(self):
        """
        Returns lastest updates
        """
        slugs = []

        def get_page(num, slugs):
            r = self.session.get(
                self.latest_updates_url,
                params=dict(
                    list=num,
                )
            )
            if r.status_code != 200:
                return None, None, None

            soup = BeautifulSoup(r.text, 'lxml')

            page_results = []
            for element in soup.select('.updates-element'):
                a_element = element.select_one('.thumb > a')
                slug = a_element.get('href').split('/')[-1]
                if slug in slugs:
                    continue
                img_element = a_element.img
                last_chapter_a_element = element.select_one('.chplinks')

                page_results.append(dict(
                    slug=f'0_{slug}',  # id is unknown at this time, use 0
                    name=img_element.get('title').strip(),
                    cover=img_element.get('src'),
                    last_chapter=last_chapter_a_element.text.strip(),
                ))
                slugs.append(slug)

            num += 1
            more = num <= SEARCH_MAX_PAGES

            return page_results, more, get_response_elapsed(r)

        delay = None
        more = True
        page = 1
        results = []
        slugs = []
        while more:
            if delay:
                time.sleep(delay)

            page_results, more, rtime = get_page(page, slugs)
            results += page_results
            delay = min(rtime * 2, DOWNLOAD_MAX_DELAY) if rtime else None
            page += 1

        return results

    def get_most_populars(self):
        """
        Returns top views
        """
        def get_page(num):
            r = self.session.get(self.most_populars_url)
            if r.status_code != 200:
                return None, None, None

            soup = BeautifulSoup(r.text, 'lxml')

            page_results = []
            for a_element in soup.select('.advanced-element > a'):
                slug = a_element.get('href').split('/')[-1]

                page_results.append(dict(
                    slug=f'0_{slug}',
                    name=a_element.get('title').strip(),
                    cover=a_element.img.get('src'),
                ))

            num += 1
            more = num <= SEARCH_MAX_PAGES

            return page_results, more, get_response_elapsed(r)

        delay = None
        more = True
        page = 1
        results = []
        while more:
            if delay:
                time.sleep(delay)

            page_results, more, rtime = get_page(page)
            results += page_results
            delay = min(rtime * 2, DOWNLOAD_MAX_DELAY) if rtime else None
            page += 1

        return results

    def search(self, term):
        r = self.session_get(
            self.search_url,
            params={
                'manga': term,
            },
            headers={
                'Referer': f'{self.base_url}/',
            }
        )
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select('a'):
            slug = a_element.get('href').split('/')[-1]

            results.append(dict(
                slug=f'0_{slug}',  # id is unknown at this time, use 0
                name=a_element.select_one('li > div > div').text.strip(),
                cover=a_element.select_one('li > img').get('src'),
            ))

        return results
