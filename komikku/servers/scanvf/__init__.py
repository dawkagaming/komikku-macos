# SPDX-FileCopyrightText: 2020-2024 GrownNed
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: GrownNed <grownned@gmail.com>

import time

from bs4 import BeautifulSoup
import requests

from komikku.consts import DOWNLOAD_MAX_DELAY
from komikku.consts import USER_AGENT
from komikku.servers import Server
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type
from komikku.utils import get_response_elapsed
from komikku.utils import is_number


class Scanvf(Server):
    id = 'scanvf'
    name = 'Scanvf'
    lang = 'fr'

    base_url = 'https://scanvf.org'
    logo_url = base_url + '/build/fav.b087d325.png'
    search_url = base_url + '/search'
    latest_updates_url = base_url + '/manga?q=u'
    most_populars_url = base_url + '/manga?q=p'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/scan/{0}'
    page_url = base_url + '/scan/{0}/{1}'

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
            scanlators=[],  # Not available
            genres=[],
            status=None,    # Not available
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        cover_element = soup.select_one('.series-picture-lg img')
        data['name'] = cover_element.get('alt').replace('Scan', '').strip()
        data['cover'] = cover_element.get('src')

        for element in soup.select('.card-series-detail div:-soup-contains("Auteur") .badge'):
            data['authors'].append(element.text.strip())

        for element in soup.select('.card-series-detail div:-soup-contains("Categories") .badge'):
            data['genres'].append(element.text.strip())

        synopsis = []
        for element in soup.select('.card div:-soup-contains("Résumé") p'):
            synopsis.append(element.text.strip())
        if synopsis:
            data['synopsis'] = '\n\n'.join(synopsis)

        # Chapters/Volumes
        for element in reversed(soup.select('.chapters-list .col-chapter')):
            a_element = element.a
            title_element = element.select_one('h5')
            date_element = title_element.div.extract()

            title = title_element.text.strip()
            num = title.split(' ')[-1].strip() if title.startswith('Chapitre ') else None
            num_volume = title.split(' ')[-1].strip() if title.startswith('Volume ') else None

            data['chapters'].append(dict(
                slug=a_element.get('href').split('/')[-1],
                title=title,
                num=num if is_number(num) else None,
                num_volume=num_volume if is_number(num_volume) else None,
                date=convert_date_string(date_element.text.strip(), format='%d-%m-%Y'),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data

        Currently, only pages are expected.
        """
        data = dict(
            pages=[],
        )
        if count := self.get_manga_chapter_page_count(chapter_slug):
            for index in range(1, count + 1):
                data['pages'].append(dict(
                    slug=str(index),
                    image=None,
                ))
            return data

        return None

    def get_manga_chapter_page_count(self, chapter_slug):
        """
        Returns the number of pages of a chapter

        Unfortunately, number of pages of chapters is not available, we must use a binary search
        """

        # First find upper
        upper = 24
        delay = None
        while True:
            if delay:
                time.sleep(delay)

            url = self.page_url.format(chapter_slug, upper)
            r = self.session_get(url)
            if r.status_code != 200:
                return None

            delay = min(get_response_elapsed(r) * 2, DOWNLOAD_MAX_DELAY)

            # If we exceed limit (last page), we are redirected to manga details page
            if r.history and r.history[-1].status_code in (301, 302):
                # On last page, website redirects to same URL with a `?bypass=1` query parameter
                if r.url.startswith(url):
                    return upper
                break

            upper *= 2

        # Binary search
        count = 0
        delay = None
        lower = 1
        while True:
            if delay:
                time.sleep(delay)

            count = lower + (upper - lower) // 2
            url = self.page_url.format(chapter_slug, count)
            r = self.session_get(url)
            if r.status_code != 200:
                return None

            delay = min(get_response_elapsed(r) * 2, DOWNLOAD_MAX_DELAY)

            # If we exceed limit (last page), we are redirected to manga details page
            if r.history and r.history[-1].status_code in (301, 302):
                # On last page, website redirects to same URL with a `?bypass=1` query parameter
                if r.url.startswith(url):
                    return count

                upper = count - 1
                continue

            lower = count + 1

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        page_url = self.page_url.format(chapter_slug, page['slug'])
        r = self.session_get(page_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        url = soup.select_one('.book-page img').get('src')
        r = self.session_get(
            url,
            headers={
                'Referer': page_url,
            }
        )

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=url.split('/')[-1].split('?')[0],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns most popular manga
        """
        r = self.session_get(self.most_populars_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        return self.parse_manga_list(r.text)

    def get_latest_updates(self):
        """
        Returns latest updated manga
        """
        r = self.session_get(self.latest_updates_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        return self.parse_manga_list(r.text)

    def parse_manga_list(self, html):
        soup = BeautifulSoup(html, 'lxml')

        results = []
        for element in soup.select('.series'):
            a_element = element.select_one('.link-series')
            if not a_element:
                continue
            img_element = element.select_one('.series-img-wrapper img')
            last_chapter_element = element.select_one('.link-chapter .chapter-name')

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
                cover=img_element.get('data-src'),
                last_chapter=last_chapter_element.text.replace('Volume', '').strip(),
            ))

        return results

    def search(self, term):
        r = self.session_get(
            self.search_url,
            params=dict(
                q=term,
            ),
            headers={
                'Referer': f'{self.base_url}/',
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type not in ('text/plain', 'text/html'):
            return None

        html = r.content.decode('unicode-escape').replace('\\', '')[1:-1]

        return self.parse_manga_list(html)
