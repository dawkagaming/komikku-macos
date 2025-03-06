# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import time

import requests

from komikku.servers import DOWNLOAD_MAX_DELAY
from komikku.servers import USER_AGENT
from komikku.servers import Server
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type
from komikku.utils import get_response_elapsed

SEARCH_RESULTS_PAGES = 10


class Perfscan(Server):
    id = 'perfscan'
    name = 'Perf Scan'
    lang = 'fr'

    base_url = 'https://perf-scan.fr'
    logo_url = base_url + '/Logo_Perf_NoText.png'
    api_url = 'https://api.perf-scan.fr'
    manga_url = base_url + '/fr/series/{0}'
    api_manga_url = api_url + '/series/{0}'
    chapter_url = base_url + '/fr/series/{0}/chapter/{1}'
    api_chapter_url = api_url + '/series/{0}/chapter/{1}'
    media_url = api_url + '/cdn'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data using API requests

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        r = self.session_get(
            self.api_manga_url.format(initial_data['slug']),
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Origin': self.base_url,
                'Referer': f'{self.base_url}/',
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()['data']

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=resp_data.get('description'),
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = resp_data['title']
        data['cover'] = f'{self.media_url}/{resp_data['cover']}'

        if resp_data.get('author'):
            data['authors'].append(resp_data['author'])
        if resp_data.get('artist'):
            data['authors'].append(resp_data['artist'])

        for genre in resp_data['SeriesGenre']:
            data['genres'].append(genre['Genre']['name'])
        if resp_data.get('Badge'):
            data['genres'].append(resp_data['Badge']['name'])

        if status := resp_data['Status']:
            if status['name'] == 'En cours':
                data['status'] = 'ongoing'
            elif status['name'] == 'Terminer':
                data['status'] = 'complete'
            elif status['name'] == 'Annulé':
                data['status'] = 'suspended'
            elif status['name'] == 'En Pause':
                data['status'] = 'hiatus'

        # Chapters
        for chapter in resp_data.get('Chapter'):
            title = chapter['title'].strip()
            if title in (None, '', '-'):
                title = f'Chapitre {chapter['index']}'

            data['chapters'].append({
                'slug': chapter['id'],
                'title': title,
                'num': chapter.get('index'),
                'date': convert_date_string(chapter['createdAt'].split('T')[0], format='%Y-%m-%d'),
            })

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Pages URLs are available in a <script> element
        """
        r = self.session_get(
            self.api_chapter_url.format(manga_slug, chapter_slug),
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Origin': self.base_url,
                'Referer': f'{self.base_url}/',
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()['data']

        data = dict(
            pages=[],
        )
        for page in resp_data['content']:
            data['pages'].append({
                'slug': page['value'],
                'url': None,
            })

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            f'{self.media_url}/{page["slug"]}',
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
            name=page['slug'],
        )

    def get_manga_list(self, term=None, orderby=None):
        def get_page(page):
            params = dict(
                take=10,
                page=page,
                type='COMIC',
            )
            if term:
                params['title'] = term
            else:
                params.update(dict(
                    ranking='POPULAR',
                    rankingType='DAILY',
                ))

            r = self.session_get(
                self.api_url + '/series',
                params=params,
                headers={
                    'Accept': 'application/json, text/plain, */*',
                    'Origin': self.base_url,
                    'Referer': f'{self.base_url}/',
                }
            )
            if r.status_code != 200:
                return None

            more = r.json()['data'] and page < SEARCH_RESULTS_PAGES

            return r.json()['data'], more, get_response_elapsed(r)

        results = []
        delay = None
        more = True
        page = 1
        while more:
            if delay:
                time.sleep(delay)

            items, more, rtime = get_page(page)
            for item in items:
                cover = item['thumbnail']
                if not cover.startswith('http'):
                    if self.media_url:
                        cover = f'{self.media_url}/{cover}'
                    else:
                        cover = f'{self.base_url}/{cover}'

                last_chapter = None
                if item.get('Chapter'):
                    last = item['Chapter'][-1]
                    last_chapter = f'Chapitre {last["index"]}'
                    if last.get('title') not in (None, '', '-'):
                        last_chapter = f'{last_chapter} : {last["title"]}'  # noqa: E203

                results.append(dict(
                    slug=item['id'],
                    name=item['title'],
                    cover=cover,
                    last_chapter=last_chapter,
                ))

            delay = min(rtime * 2, DOWNLOAD_MAX_DELAY) if rtime else None
            page += 1

        return results

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns most popular mangas
        """
        return self.get_manga_list(orderby='popular')

    def search(self, term):
        return self.get_manga_list(term=term)
