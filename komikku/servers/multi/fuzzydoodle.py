# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# Supported servers:
# Lelscan-VF [FR]
# FleksyScans [EN]
# Scylla Scans [EN]

from bs4 import BeautifulSoup
import requests
from urllib.parse import parse_qs
from urllib.parse import urlparse

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type
from komikku.servers.utils import get_soup_element_inner_text

# https://github.com/jhin1m/fuzzy-doodle


class FuzzyDoodle(Server):
    base_url: str = None
    search_url: str = None
    manga_url: str = None
    chapter_url: str = None

    # Selectors
    imgs_src_attrs: list = ['src', 'data-src']

    search_results_selector: str = None
    search_link_selector: str = None
    search_cover_img_selector: str = None

    most_popular_results_selector: str = None
    most_popular_link_selector: str = None
    most_popular_cover_img_selector: str = None

    latest_updates_results_selector: str = None
    latest_updates_link_selector: str = None
    latest_updates_cover_img_selector: str = None

    details_name_selector: str = None
    details_cover_selector: str = None
    details_status_selector: str = None
    details_author_selector: str = None
    details_artist_selector: str = None
    details_type_selector: str = None
    details_genres_selector: str = None
    details_synopsis_selector: str = None

    chapters_selector: str = None
    chapters_title_selector: str = None
    chapters_date_selector: str = None

    chapter_pages_selector: str = None

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = {
                'User-Agent': USER_AGENT,
            }

    def get_img_src(self, element):
        for attr in self.imgs_src_attrs:
            if src := element.get(attr):
                return src

        return None

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug'], 1))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
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
            cover=None,
        ))

        soup = BeautifulSoup(r.text, 'lxml')

        data['name'] = get_soup_element_inner_text(soup.select_one(self.details_name_selector), recursive=False)
        data['cover'] = self.get_img_src(soup.select_one(self.details_cover_selector))

        # Status
        status = soup.select_one(self.details_status_selector).text.strip()
        if status in ('Completed', 'Terminé'):
            data['status'] = 'complete'
        elif status in ('Ongoing', 'En cours'):
            data['status'] = 'ongoing'
        elif status in ('On-hold', ):
            data['status'] = 'suspended'
        elif status in ('Cancelled', ):
            data['status'] = 'suspended'
        elif status in ('Dropped', ):
            data['status'] = 'suspended'
        elif status in ('Hiatus'):
            data['status'] = 'hiatus'

        # Authors
        if element := soup.select_one(self.details_author_selector):
            data['authors'].append(element.text.strip())
        if element := soup.select_one(self.details_artist_selector):
            artist = element.text.strip()
            if artist not in data['authors']:
                data['authors'].append(artist)

        # Genres
        if a_elements := soup.select(self.details_genres_selector):
            for a_element in a_elements:
                data['genres'].append(a_element.text.strip())

        if element := soup.select_one(self.details_type_selector):
            type = element.text.strip()
            if type not in data['genres']:
                data['genres'].append(type)

        # Synopsis
        if elements := soup.select(self.details_synopsis_selector):
            synopsis = []
            for element in elements:
                chunk = element.text.strip()
                if chunk:
                    synopsis.append(chunk)
            data['synopsis'] = '\n\n'.join(synopsis)

        # Chapters
        data['chapters'] = self.get_manga_chapters_data(data['slug'], soup=soup)

        return data

    def get_manga_chapters_data(self, slug, num=None, soup=None, chapters=None):
        if chapters is None:
            chapters = []

        if soup is None and num is not None:
            r = self.session_get(self.manga_url.format(slug), params=dict(page=num))
            if r.status_code != 200:
                return None

            mime_type = get_buffer_mime_type(r.content)
            if mime_type != 'text/html':
                return None

            soup = BeautifulSoup(r.text, 'lxml')

        for a_element in soup.select(self.chapters_selector):
            date = a_element.select_one(self.chapters_date_selector).text.strip()

            chapters.append(dict(
                slug=a_element.get('href').split('/')[-1],
                title=a_element.select_one(self.chapters_title_selector).text.strip(),
                date=convert_date_string(date),
            ))

        if next_element := soup.select_one('#chapters-list nav > ul.pagination > li:last-child'):
            if next_url := next_element.get('onclick'):
                next_url = next_url[22:-1]
                next_num = parse_qs(urlparse(next_url).query)['page'][0]
                self.get_manga_chapters_data(slug, num=next_num, chapters=chapters)

        return list(reversed(chapters))

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data

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
        for index, img_element in enumerate(soup.select(self.chapter_pages_selector)):
            data['pages'].append(dict(
                slug=None,
                image=self.get_img_src(img_element),
                index=index + 1,
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
            name=f'{page["index"]:04d}.{mime_type.split("/")[-1]}',
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_latest_updates(self):
        """
        Returns daily updates
        """
        r = self.session.get(self.base_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.select(self.latest_updates_results_selector):
            a_element = element.select_one(self.latest_updates_link_selector)
            name = element.select_one(self.latest_updates_cover_img_selector).get('alt').strip()
            img_element = element.select_one(self.latest_updates_cover_img_selector)
            last_chapter_element = element.select_one(self.latest_updates_last_chapter_selector)

            results.append(dict(
                name=name,
                slug=a_element.get('href').split('/')[-1],
                cover=self.get_img_src(img_element),
                last_chapter='#' + last_chapter_element.text.strip(),
            ))

        return results

    def get_most_populars(self):
        """
        Returns popular manga
        """
        r = self.session.get(self.base_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.select(self.most_popular_results_selector):
            a_element = element.select_one(self.most_popular_link_selector)
            name = element.select_one(self.most_popular_cover_img_selector).get('alt').strip()
            img_element = element.select_one(self.most_popular_cover_img_selector)

            results.append(dict(
                name=name,
                slug=a_element.get('href').split('/')[-1],
                cover=self.get_img_src(img_element),
            ))

        return results

    def search(self, term):
        r = self.session.get(
            self.search_url,
            params=dict(
                title=term,
            ),
            headers={
                'Referer': f'{self.base_url}/',
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.select(self.search_results_selector):
            a_element = element.select_one(self.search_link_selector)
            name = element.select_one(self.search_cover_img_selector).get('alt').strip()
            img_element = element.select_one(self.search_cover_img_selector)

            results.append(dict(
                name=name,
                slug=a_element.get('href').split('/')[-1],
                cover=self.get_img_src(img_element),
            ))

        return results
