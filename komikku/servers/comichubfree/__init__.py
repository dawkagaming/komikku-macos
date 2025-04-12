# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import requests
import time

from komikku.servers import DOWNLOAD_MAX_DELAY
from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type
from komikku.utils import get_response_elapsed
from komikku.utils import is_number

# Similar to dead server comicextra


class Comichubfree(Server):
    id = 'comichubfree'
    name = 'ComicHubFree'
    lang = 'en'

    base_url = 'https://comichubfree.com'
    logo_url = base_url + '/favicon.png'
    search_url = base_url + '/search-comic'
    latest_updates_url = base_url + '/comic-updates'
    most_populars_url = base_url + '/popular-comic'
    manga_url = base_url + '/comic/{0}'
    chapter_url = base_url + '/{0}/{1}/all'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = {
                'User-Agent': USER_AGENT,
            }

    def get_manga_data(self, initial_data):
        """
        Returns comic data by scraping manga HTML page content

        Initial data should contain at least comic's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug']))
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

        data['name'] = soup.select_one('.breadcrumb li:last-child span[itemprop="name"]').text.strip()
        data['cover'] = soup.select_one('.movie-image img').get('data-src')

        for element in soup.select('.movie-dl dd.status'):
            status = element.text.strip().lower()
            if status == 'completed':
                data['status'] = 'complete'
            elif status == 'ongoing':
                data['status'] = 'ongoing'

        if element := soup.select_one('.movie-meta-info dt:-soup-contains("Author")'):
            data['authors'].append(element.find_next_siblings()[0].text.strip())

        if element := soup.select_one('.movie-meta-info dt:-soup-contains("Genres")'):
            for a_element in element.find_next_siblings()[0].select('a'):
                data['genres'].append(a_element.text.strip())

        data['synopsis'] = soup.select_one('#film-content').text.strip()

        # Chapters (Issues)
        data['chapters'] = self.get_manga_chapters_data(data['slug'], soup=soup)

        return data

    def get_manga_chapters_data(self, slug, page=None, soup=None, chapters=None):
        if chapters is None:
            chapters = []

        if soup is None:
            r = self.session_get(self.manga_url.format(slug), params=dict(page=page))
            if r.status_code != 200:
                return None

            mime_type = get_buffer_mime_type(r.content)
            if mime_type != 'text/html':
                return None

            rtime = get_response_elapsed(r)
            soup = BeautifulSoup(r.text, 'lxml')
        else:
            rtime = None

        for tr_element in soup.select('#list tr'):
            a_element = tr_element.select_one('a')
            td_elements = tr_element.select('td')

            chapter_slug = a_element.get('href').split('/')[-1]
            num = chapter_slug.replace('issue-', '')

            chapters.append(dict(
                slug=chapter_slug,
                title=a_element.text.strip(),
                num=num if is_number(num) else None,
                date=convert_date_string(td_elements[1].text.strip(), '%d-%b-%Y', languages=[self.lang]),
            ))

        if next_element := soup.select_one('ul.pagination > li > a[rel="next"]'):
            if rtime:
                time.sleep(min(rtime * 4, DOWNLOAD_MAX_DELAY))

            next_page = next_element.get('href').split('=')[-1]
            self.get_manga_chapters_data(slug, page=next_page, chapters=chapters)

        return list(reversed(chapters))

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns comic chapter data

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for index, img_element in enumerate(soup.select('.chapter-container .page-chapter img')):
            data['pages'].append(dict(
                image=img_element.get('data-src').strip(),
                slug=None,
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
            name=f"{page['index']}.{mime_type.split('/')[1]}",
        )

    def get_manga_url(self, slug, url):
        """
        Returns comic absolute URL
        """
        return self.manga_url.format(slug)

    def get_latest_updates(self):
        """
        Returns daily updates
        """
        r = self.session.get(
            self.latest_updates_url,
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
        for element in soup.select('.hl-box'):
            a_element = element.select_one('a')
            last_a_element = element.select_one('.hlb-list a')

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
                last_chapter=last_a_element.text.strip() if last_a_element else None,
            ))

        return results

    def get_most_populars(self):
        """
        Returns popular comics
        """
        r = self.session.get(
            self.most_populars_url,
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
        for element in soup.select('.cartoon-box'):
            a_element = element.select_one('.mb-right h3 a')
            img_element = element.select_one('.image img')
            nb_chapters_element = element.select_one('.mb-right .detail')

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
                cover=img_element.get('data-src'),
                nb_chapters=nb_chapters_element.text.split()[0],
            ))

        return results

    def search(self, term):
        r = self.session.get(
            self.search_url,
            params=dict(
                key=term,
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
        for element in soup.select('.cartoon-box'):
            a_element = element.select_one('.mb-right h3 a')
            img_element = element.select_one('.image img')
            nb_chapters_element = element.select_one('.mb-right .detail')

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
                cover=img_element.get('data-src'),
                nb_chapters=nb_chapters_element.text.split()[0],
            ))

        return results
