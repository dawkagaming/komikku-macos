# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# Hean CMS

# Supported servers:
# EZmanga [EN]
# Mode Scanlator [pt_BR] (disabled)
# Reaper Scans [EN] (disabled)
# Reaper Scans [pt_BR] (disabled)

import json
import logging
import re
import time

from bs4 import BeautifulSoup
import requests

from komikku.consts import DOWNLOAD_MAX_DELAY
from komikku.consts import USER_AGENT
from komikku.servers import Server
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type
from komikku.utils import get_response_elapsed
from komikku.webview import CompleteChallenge

logger = logging.getLogger('komikku.servers.multi.heancms')


def extract_info_from_script(soup, keyword):
    info = None

    for script_element in soup.select('script'):
        script = script_element.string
        if not script or not script.startswith('self.__next_f.push([1,') or keyword not in script:
            continue

        line = script.strip().replace('self.__next_f.push([1,', '')

        start = 0
        for c in line:
            if c in ('{', '['):
                break
            start += 1

        line = line[start:-3]

        try:
            info = json.loads(f'"{line}"')
        except Exception as e:
            logger.debug(f'ERROR: {line}')
            logger.debug(e)
        break

    return info


class HeanCMS(Server):
    base_url: str
    api_url: str
    api_version: int
    manga_url: str = None
    chapter_url: str = None
    api_chapters_url: str = None
    media_url: str = None

    date_format = '%m/%d/%Y'
    re_serie_id = r'.*{"series_id":(\d*).*'

    name_css_path: str
    cover_css_path: str
    authors_css_path: str
    synopsis_css_path: str

    def __init__(self):
        if self.manga_url is None:
            self.manga_url = self.base_url + '/series/{0}'
        if self.chapter_url is None:
            self.chapter_url = self.base_url + '/series/{0}/{1}'
        if self.api_chapters_url is None:
            self.api_chapters_url = self.api_url + '/chapter/query'

        if self.session is None and not self.has_cf:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': USER_AGENT})

    @staticmethod
    def extract_chapter_nums_from_slug(slug):
        """Extract chapter num from slug

        Volume num is not available
        """
        re_nums = r'^((\w+)-)?(\d+)(-(\d+))?.*'

        if matches := re.search(re_nums, slug):
            if num := matches.group(3):
                num = f'{int(num)}'

                if num_dec := matches.group(5):
                    num = f'{num}.{int(num_dec)}'

                return num, None

        return None, None

    @CompleteChallenge()
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

        if info := extract_info_from_script(soup, 'series_slug'):
            # Extract serie_id
            if matches := re.search(self.re_serie_id, info):
                serie_id = matches.group(1)
            else:
                return None

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

        data['name'] = soup.find(self.name_css_path).text.strip()
        if img_element := soup.select_one(self.cover_css_path):
            data['cover'] = img_element.get('src')
            if not data['cover'].startswith('http'):
                if self.media_url:
                    data['cover'] = self.media_url + data['cover']
                else:
                    data['cover'] = self.base_url + data['cover']

        # Details
        if element := soup.select_one(self.authors_css_path):
            for author in element.text.split('|'):
                data['authors'].append(author.strip())

        data['synopsis'] = soup.select_one(self.synopsis_css_path).text.strip()

        # Chapters
        data['chapters'] = self.get_manga_chapters_data(serie_id)

        return data

    def get_manga_chapters_data(self, serie_id):
        """
        Returns manga chapters list via API
        """
        chapters = []

        def get_page(serie_id, page):
            if self.api_version == 1:
                r = self.session_get(
                    self.api_chapters_url,
                    params=dict(
                        page=page,
                        perPage=100,
                        series_id=serie_id,
                    )
                )
            elif self.api_version == 2:
                r = self.session_get(
                    self.api_chapters_url.format(serie_id),
                    params=dict(
                        page=page,
                        perPage=100,
                    )
                )
            if r.status_code != 200:
                return None, False, None

            data = r.json()
            if not data.get('data'):
                return None, False, None

            more = data.get('meta') and data['meta']['current_page'] != data['meta']['last_page']

            return data['data'], more, get_response_elapsed(r)

        chapters = []
        delay = None
        more = True
        page = 1
        while more:
            if delay:
                time.sleep(delay)

            chapters_page, more, rtime = get_page(serie_id, page)
            if chapters_page:
                for chapter in chapters_page:
                    if chapter['price'] > 0:
                        continue

                    num, _num_volume = self.extract_chapter_nums_from_slug(chapter['chapter_slug'])

                    chapters.append(dict(
                        slug=chapter['chapter_slug'],
                        title=chapter['chapter_name'],
                        num=num,
                        date=convert_date_string(chapter['created_at'].split('T')[0], self.date_format) if 'created_at' in chapter else None,
                    ))
                page += 1
                delay = min(rtime * 2, DOWNLOAD_MAX_DELAY) if rtime else None

            elif chapters_page is None:
                # Failed to retrieve a chapters list page, abort
                break

        return list(reversed(chapters))

    @CompleteChallenge()
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Pages URLs are available in a <script> element
        """
        r = self.session_get(
            self.chapter_url.format(manga_slug, chapter_slug),
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

        if info := extract_info_from_script(soup, 'API_Response'):
            info = json.loads(info)

            data = dict(
                pages=[],
            )
            for url in info[1][3]['children'][1][3]['children'][1][3]['API_Response']['chapter']['chapter_data']['images']:
                data['pages'].append(dict(
                    slug=None,
                    image=url,
                ))

            return data

        return None

    @CompleteChallenge()
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

    @CompleteChallenge()
    def get_latest_updates(self):
        """
        Returns latest updates
        """
        return self.get_manga_list(orderby='latest')

    def get_manga_list(self, term=None, orderby=None):
        params = dict(
            adult='true',
            series_type='Comic',
            status='All',
            tags_ids='[]',
        )
        if term:
            params['query_string'] = term
        else:
            params.update(dict(
                visibility='Public',
                order='desc',
                page=1,
                perPage=20,
            ))
            if orderby == 'latest':
                params['orderBy'] = 'latest'
            elif orderby == 'popular':
                params['orderBy'] = 'total_views'

        r = self.session_get(
            self.api_url + '/query',
            params=params,
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Origin': self.base_url,
                'Referer': f'{self.base_url}/',
            }
        )
        if r.status_code != 200:
            return None

        results = []
        for item in r.json()['data']:
            cover = item['thumbnail']
            if not cover.startswith('http'):
                if self.media_url:
                    cover = f'{self.media_url}/{cover}'
                else:
                    cover = f'{self.base_url}/{cover}'

            results.append(dict(
                slug=item['series_slug'],
                name=item['title'],
                cover=cover,
                last_chapter=item['chapters'][0]['chapter_name'] if item.get('chapters') else None,
            ))

        return results

    @CompleteChallenge()
    def get_most_populars(self):
        """
        Returns most popular mangas
        """
        return self.get_manga_list(orderby='popular')

    @CompleteChallenge()
    def search(self, term):
        return self.get_manga_list(term=term)
