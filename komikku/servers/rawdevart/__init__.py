# Copyright (C) 2024-2024 Zhao Se
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Zhao Se <zhaose233@outlook.com>

import json
import requests
from bs4 import BeautifulSoup

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type


class Rawdevart(Server):
    id = 'rawdevart'
    name = 'Rawdevart'
    lang = 'ja'
    is_nsfw = True

    base_url = 'https://rawdevart.art'
    search_url = 'https://rawdevart.art/ajax/search-manga'
    search_url_webpage = 'https://rawdevart.art/search?query={0}'
    manga_url = 'https://rawdevart.art/spa/manga/{0}'
    chapter_url = manga_url + '/{1}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Get full manga data by parsing the response of the API.
        """
        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None
        r_decoded = json.loads(r.content)

        authors = [
            author_info['author_name'] for author_info in r_decoded['authors']
        ]
        synopsis = r_decoded['detail']['manga_description']
        genres = [tag_info['tag_name'] for tag_info in r_decoded['tags']]

        chapters = []
        for chapter_info in r_decoded['chapters']:
            slug = chapter_info['chapter_number']
            title = "Chapter " + str(slug)
            date = convert_date_string(chapter_info['chapter_date_published'])

            chapters.append(dict(slug=str(slug), title=title, date=date))

        data = dict(name=r_decoded['detail']['manga_name'],
                    slug=initial_data['slug'],
                    url=self.search_url_webpage.format(r_decoded['detail']['manga_name']),
                    authors=authors,
                    genres=genres,
                    synopsis=synopsis,
                    chapters=chapters,
                    server_id=self.id,
                    cover=r_decoded['detail']['manga_cover_img_full'])

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug,
                               chapter_url):
        """
        Returns manga chapter data by parsing the response of the API.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r.status_code != 200:
            return None
        r_decoded = json.loads(r.content)

        soup = BeautifulSoup(r_decoded['chapter_detail']['chapter_content'],
                             "html.parser")
        pages = []
        index = 1
        for canvas in soup.find_all('canvas'):
            image = canvas.get('data-srcset')
            pages.append(dict(image=image, index=index))
            index += 1

        data = dict(pages=pages)
        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name,
                                     chapter_slug, page):
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
            name='{0:03d}.{1}'.format(page['index'],
                                      mime_type.split('/')[-1]),
        )

    def get_manga_url(self, slug, url):
        return url  # It's hard to get the absolute webpage url

    def search(self, term=None):
        """
        Search for mangas
        """
        r = self.session_get(self.search_url, params=dict(query=term))
        if r.status_code != 200:
            return None
        r_decoded = json.loads(r.content)

        data = []
        for manga_info in r_decoded:
            slug = manga_info['manga_id']
            name = manga_info['manga_name']
            cover = manga_info['manga_cover_img']
            nb_chapters = manga_info['chapter_number']

            data.append(
                dict(slug=str(slug),
                     name=name,
                     cover=cover,
                     nb_chapters=nb_chapters))

        return data
