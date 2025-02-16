# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import datetime
import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

from komikku.servers import DOWNLOAD_MAX_DELAY
from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.utils import get_buffer_mime_type
from komikku.utils import get_response_elapsed


class Comicfans(Server):
    id = 'comicfans'
    name = 'Comic Fans'
    lang = 'en'
    status = 'disabled'

    base_url = 'https://comicfans.io'
    api_base_url = 'https://api.comicfans.io/comic-backend/api/v1/content'
    static_base_url = 'https://static.comicfans.io'

    manga_url = base_url + '/comic/{0}'
    chapter_url = base_url + '/episode/{0}'
    api_search_url = api_base_url + '/books/search'
    api_manga_url = api_base_url + '/books/{0}'
    api_chapters_url = api_base_url + '/chapters/page?sortDirection=ASC&bookId={0}&pageNumber=1&pageSize=9999'
    api_chapter_url = api_base_url + '/chapters/{0}'

    api_headers = {
        'Accept': '*/*',
        'Host': urlparse(api_base_url).netloc,
        'Origin': base_url,
        'Referer': f'{base_url}/',
        'Site-Domain': 'www.' + urlparse(base_url).netloc,
    }

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = {
                'User-Agent': USER_AGENT,
            }

    def get_manga_data(self, initial_data):
        """
        Returns manga data retrieved via API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.api_manga_url.format(initial_data['slug']), headers=self.api_headers)
        if r.status_code != 200:
            return None

        resp_json = r.json()
        if resp_json['code'] != 0:
            return None

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],  # not available
            genres=[],  # not available, API endpoint seems incomplete
            status=None,  # not available API endpoint seems incomplete
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = resp_json['data']['title']
        data['cover'] = f'{self.static_base_url}/{resp_json["data"]["coverImgUrl"]}'

        # Authors
        if author := resp_json['data'].get('authorPseudonym'):
            data['authors'].append(author)

        # Synopsis
        data['synopsis'] = resp_json['data']['synopsis']

        # Chapters
        r = self.session_get(self.api_chapters_url.format(initial_data['slug']), headers=self.api_headers)
        if r.status_code != 200:
            return None

        resp_json = r.json()
        if resp_json['code'] != 0:
            return None

        for chapter in resp_json['data']['list']:
            data['chapters'].append(dict(
                slug=str(chapter['id']),
                title=chapter['title'],
                num=chapter['chapterOrder'],
                date=datetime.datetime.fromtimestamp(chapter['updateTime'] / 1000).date(),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data retrieved via API

        Currently, only pages are expected.
        """
        r = self.session_get(self.api_chapter_url.format(chapter_slug), headers=self.api_headers)
        if r.status_code != 200:
            return None

        resp_json = r.json()
        if resp_json['code'] != 0:
            return None

        data = dict(
            pages=[],
        )
        for index, page in enumerate(resp_json['data']['comicImageList']):
            data['pages'].append(dict(
                slug=None,
                image=page['imageUrl'],
                index=index + 1,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            f'{self.static_base_url}/{page["image"]}',
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
            name=f'{page["index"]:04d}.{mime_type.split("/")[-1]}',  # noqa: E231
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
        r = self.session.get(self.base_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        slugs = []
        for element in soup.select('#widgets div:nth-child(2) .book'):
            a_element = element.select_one('.book-name a')
            img_element = element.select_one('img.book-cover')

            slug = a_element.get('href').split('/')[-1].split('-')[0]
            if slug in slugs:
                continue

            results.append(dict(
                slug=slug,
                name=a_element.text.strip(),
                cover=img_element.get('src'),
            ))
            slugs.append(slug)

        return results

    def search(self, term):
        def get_page(num):
            r = self.session.get(
                self.api_search_url.format(term),
                params=dict(
                    pageNumber=num,
                    pageSize=10,
                    keyWord=term,
                ),
                headers=self.api_headers
            )
            if r.status_code != 200:
                return None, None

            resp_json = r.json()
            if resp_json['code'] != 0:
                return None, None

            return resp_json['data'], get_response_elapsed(r)

        delay = None
        more = True
        page_num = 1
        results = []
        while more:
            if delay:
                time.sleep(delay)

            data, rtime = get_page(page_num)
            if data:
                for item in data['list']:
                    results.append(dict(
                        slug=str(item['id']),
                        name=item['title'],
                        cover=f'{self.static_base_url}/{item["coverImgUrl"]}',
                        last_chapter=f'#{item["lastUpdateChapterOrder"]} {item["lastUpdateChapterTitle"]}',
                        nb_chapters=item['publishedChapters'],
                    ))

            more = data and data['totalPages'] > page_num
            delay = min(rtime * 2, DOWNLOAD_MAX_DELAY) if rtime else None
            page_num += 1

        return results
