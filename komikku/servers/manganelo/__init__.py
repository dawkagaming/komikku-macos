# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_soup_element_inner_text
from komikku.utils import get_buffer_mime_type
from komikku.utils import is_number

# NOTE: https://mangakakalot.gg seems to be a clone (same IP)


class Manganelo(Server):
    id = 'manganelo'
    name = 'MangaNato (MangaNelo)'
    lang = 'en'
    long_strip_genres = ['Webtoons', ]

    base_url = 'https://www.manganato.gg'
    logo_url = base_url + '/images/favicon.ico'
    search_url = base_url + '/home/search/json'
    manga_list_url = base_url + '/genre/all'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/chapter-{1}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': USER_AGENT})

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

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        # Name & cover
        data['name'] = soup.select_one('.manga-info-text h1').text.strip()
        data['cover'] = soup.select_one('.manga-info-pic img').get('src')

        # Details
        for li_element in soup.select('ul.manga-info-text li'):
            try:
                label, value = li_element.text.split(':', 1)
            except Exception:
                continue

            label = label.strip()

            if label.startswith('Author'):
                data['authors'] = [t.strip() for t in value.split(',') if t.strip() != 'Unknown']
            elif label.startswith('Genres'):
                data['genres'] = [t.strip() for t in value.split(',')]
            elif label.startswith('Status'):
                status = value.strip().lower()
                if status == 'completed':
                    data['status'] = 'complete'
                elif status == 'ongoing':
                    data['status'] = 'ongoing'

        # Synopsis
        data['synopsis'] = get_soup_element_inner_text(soup.select_one('#contentBox'), recursive=False)

        # Chapters
        for element in reversed(soup.select('.chapter-list .row')):
            a_element = element.select_one('a')
            slug = a_element.get('href').split('/')[-1].split('-')[-1]

            data['chapters'].append(dict(
                slug=slug,
                title=a_element.text.strip(),
                num=slug if is_number(slug) else None,
                date=convert_date_string(element.select_one('span:last-child').get('title').split()[0], format='%b-%d-%Y'),
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
        for img in soup.select('.container-chapter-reader img'):
            data['pages'].append(dict(
                slug=None,  # slug can't be used to forge image URL
                image=img.get('src'),
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page['image'],
            headers={
                'Accept': 'image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5',
                'Referer': f'{self.base_url}/',
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
        Returns latest manga list
        """
        return self.get_manga_list(orderby='latest')

    def get_most_populars(self):
        """
        Returns hot manga list
        """
        return self.get_manga_list(orderby='topview')

    def get_manga_list(self, orderby=None):
        """
        Returns hot manga list
        """
        params = {
            'state': 'all',
            'page': 1
        }
        if orderby:
            params['type'] = orderby

        r = self.session_get(
            self.manga_list_url,
            params=params,
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.select('.list-truyen-item-wrap'):
            link_element = element.h3.a
            link_cover_element = element.a
            last_chapter_link_element = element.select_one('.list-story-item-wrap-chapter')
            results.append(dict(
                name=link_element.get('title').strip(),
                slug=link_element.get('href').split('/')[-1],
                cover=link_cover_element.img.get('src'),
                last_chapter=last_chapter_link_element.text.strip().split()[-1],
            ))

        return results

    def search(self, term):
        r = self.session_get(
            self.search_url,
            params=dict(searchword=term.lower().replace(' ', '_')),
            headers={
                'Referer': f'{self.base_url}/',
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        if r.status_code != 200:
            return None

        data = r.json()

        results = []
        for item in data:
            results.append(dict(
                slug=item['slug'],
                name=item['name'],
                cover=item['thumb'],
                last_chapter=item['chapterLatest'].split()[-1],
            ))

        return results
