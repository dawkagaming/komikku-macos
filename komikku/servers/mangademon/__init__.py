# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import time

from bs4 import BeautifulSoup
import requests

from komikku.servers import DOWNLOAD_MAX_DELAY
from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type
from komikku.servers.utils import get_response_elapsed

SEARCH_MAX_PAGES = 2


class Mangademon(Server):
    id = 'mangademon'
    name = 'Manga Demon'
    lang = 'en'

    slugs_postfix = '-VA54'

    base_url = 'https://mgdemon.org'
    search_url = base_url + '/search.php'
    latest_updates_url = base_url + '/updates.php'
    most_populars_url = base_url + '/browse.php'
    manga_url = base_url + '/manga/{0}' + slugs_postfix
    chapter_url = base_url + '/manga/{0}/chapter/{1}' + slugs_postfix

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
            cover=None,
        ))

        data['name'] = soup.select_one('h1.novel-title').text.strip()
        data['cover'] = soup.select_one('img#thumbonail').get('src')

        # Genres
        for a_element in soup.select('.categories ul li a'):
            genre = a_element.text.strip()
            if genre not in data['genres']:
                data['genres'].append(genre)

        # Status
        if element := soup.select_one('.header-stats > span:-soup-contains("Status") strong'):
            status = element.text.strip()
            if status == 'Ongoing':
                data['status'] = 'ongoing'
            elif status == 'Completed':
                data['status'] = 'complete'

        # Authors
        if element := soup.select_one('.author span:last-child'):
            author = element.text.strip()
            if author.lower() not in ('coming soon', 'updating'):
                data['authors'].append(author)

        # Synopsis
        if element := soup.select_one('#info p.description'):
            data['synopsis'] = element.text.strip()

        # Chapters
        for element in reversed(soup.select('#chapters ul.chapter-list li')):
            data['chapters'].append(dict(
                slug=element.get('data-chapterno'),
                title=element.select_one('.chapter-title').text.strip(),
                date=convert_date_string(element.select_one('.chapter-update').get('date'), format='%Y-%m-%d'),
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

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for img_element in soup.select('.imgholder'):
            data['pages'].append(dict(
                slug=None,
                image=img_element.get('src'),
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

    def get_latest_updates(self):
        """
        Returns recent Updates
        """
        slugs = []

        def get_page(num, slugs):
            r = self.session.get(
                self.latest_updates_url,
                params=dict(
                    list=num,
                ),
                headers={
                    'Referer': f'{self.latest_updates_url}',
                }
            )
            if r.status_code != 200:
                return None, None, None

            soup = BeautifulSoup(r.text, 'lxml')

            page_results = []
            for element in soup.select('#content ul li'):
                a_element = element.select_one('.novel-title > a')
                slug = a_element.get('href').split('/')[-1].replace(self.slugs_postfix, '')
                if slug in slugs:
                    continue
                img_element = element.select_one('.novel-cover > img')
                last_chapter_a_element = element.select_one('.chapternumber > a')

                page_results.append(dict(
                    slug=slug,
                    name=a_element.text.strip(),
                    cover=img_element.get('src'),
                    last_chapter=last_chapter_a_element.text.replace('Chapter', '').strip(),
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
            r = self.session.get(
                self.most_populars_url,
                params=dict(
                    list=num,
                    status='all',
                    orderby='VIEWS DESC',
                ),
                headers={
                    'Referer': f'{self.most_populars_url}',
                }
            )
            if r.status_code != 200:
                return None, None, None

            soup = BeautifulSoup(r.text, 'lxml')

            page_results = []
            for element in soup.select('#content ul li'):
                a_element = element.select_one('.novel-title > a')
                slug = a_element.get('href').split('/')[-1].replace(self.slugs_postfix, '')
                img_element = element.select_one('.novel-cover > img')
                last_chapter_a_element = element.select_one('.chapternumber > a')

                page_results.append(dict(
                    slug=slug,
                    name=a_element.text.strip(),
                    cover=img_element.get('src'),
                    last_chapter=last_chapter_a_element.text.replace('Chapter', '').strip(),
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
        for a_element in soup.select('a.boxsizing'):
            results.append(dict(
                slug=a_element.get('href').split('/')[-1].replace(self.slugs_postfix, ''),
                name=a_element.text.strip(),
            ))

        return results
