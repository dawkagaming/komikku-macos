# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import base64
import logging
import time

from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import modes
try:
    # This server requires JA3/TLS and HTTP2 fingerprints impersonation
    from curl_cffi import requests
except Exception:
    # Server will be disabled
    requests = None
import unidecode

from komikku.servers import Server
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type
from komikku.servers.utils import sojson4_decode

SEARCH_RESULTS_PAGES = 5
MOST_POPULAR_RESULTS_PAGES = 2
LATEST_UPDATES_RESULTS_PAGES = 5

logger = logging.getLogger('komikku.servers.mangago')


class Mangago(Server):
    id = 'mangago'
    name = 'Mangago'
    lang = 'en'
    status = 'enabled' if requests is not None else 'disabled'

    base_url = 'https://www.mangago.me'
    search_url = base_url + '/r/l_search/'
    latest_updates_url = base_url + '/list/latest/all/{0}/'
    most_populars_url = base_url + '/topmanga/'
    manga_url = base_url + '/read-manga/{0}/'
    chapter_url = base_url + '/read-manga/{0}/{1}/'

    def __init__(self):
        if self.session is None and requests is not None:
            self.session = requests.Session(allow_redirects=True, impersonate='chrome', timeout=(5, 10))

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

        data['name'] = soup.select_one('h1').text.strip()
        data['cover'] = soup.select_one('.cover img').get('src')

        # Details
        for element in soup.select('.manga_right td'):
            label = element.label.text.strip()

            if label.startswith('Author'):
                for a_element in element.select('a'):
                    author = a_element.text.strip()
                    if not author:
                        continue
                    data['authors'].append(author)
            elif label.startswith('Genre'):
                for a_element in element.select('a'):
                    data['genres'].append(a_element.text.strip())
            elif label.startswith('Status'):
                value = element.span.text.strip().lower()

                if value == 'ongoing':
                    data['status'] = 'ongoing'
                elif value == 'completed':
                    data['status'] = 'complete'

        # Synopsis
        if synopsis_element := soup.select_one('.manga_summary'):
            data['synopsis'] = synopsis_element.text.strip()

        # Chapters
        for tr_element in reversed(soup.select('#chapter_table tr')):
            td_elements = tr_element.select('td')
            slug_element = td_elements[0].select_one('a')
            data['chapters'].append(dict(
                slug='/'.join(slug_element.get('href').split('/')[-4:-1]),
                title=unidecode.unidecode(slug_element.text.strip()),
                date=convert_date_string(td_elements[2].text.strip(), format='%b %d, %Y'),
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

        # Get page URLs list: AES encryption + base64 encoding
        imgsrcs = None
        for script_element in soup.select('script'):
            script = script_element.string
            if not script or 'var imgsrcs' not in script:
                continue

            for line in script.split('\n'):
                line = line.strip()
                if line.startswith('var imgsrcs'):
                    imgsrcs = line.split(' = ')[1][1:-2]
                    break

            break

        if imgsrcs is None:
            logger.warning('Failed to get encrypted pages URLs list')
            return None

        # Get URL of JS file in charge of decryption (sojson.v4 obfuscated)
        chapterjs_url = None
        for script_element in soup.select('script'):
            src = script_element.get('src')
            if src and 'chapter.js' in src:
                chapterjs_url = src
                break

        if chapterjs_url is None:
            logger.warning('Failed to get URL of JS file in charge of decryption')
            return None

        # Get file and deobfuscate it
        r = self.session_get(chapterjs_url)
        if 'sojson.v4' not in r.text:
            logger.warning('JS file in charge of decryption is not obfuscated with sojson.v4!')
            return None

        js_code = sojson4_decode(r.text)

        # Parse JS code to get AES key and iv (both in hexadecimal)
        key = None
        iv = None
        for line in js_code.split('\n'):
            if 'var key = CryptoJS' in line:
                key = line.split('"')[-2]
            if 'var iv  = CryptoJS' in line:
                iv = line.split('"')[-2]
            if iv and key:
                break

        if key is None or iv is None:
            logger.warning('Failed to get AES key and/or iv')
            return None

        key = bytes.fromhex(key)
        iv = bytes.fromhex(iv)
        imgsrcs = base64.b64decode(imgsrcs)

        # Decrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        imgsrcs = decryptor.update(imgsrcs) + decryptor.finalize()
        imgsrcs = imgsrcs.decode('utf-8').rstrip('\x00').split(',')

        data = dict(
            pages=[],
        )
        for url in imgsrcs:
            data['pages'].append(dict(
                slug=None,
                image=url,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        # Scrap HTML page to get image url
        r = self.session_get(page['image'])
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
        Returns Latest Updates list
        """
        def get_page(page):
            r = self.session_get(self.latest_updates_url.format(page))
            if r.status_code != 200:
                return None, False

            soup = BeautifulSoup(r.text, 'lxml')

            import unidecode

            items = []
            for element in soup.select('#search_list li .box'):
                a_element = element.select_one('a.thm-effect')
                if last_chapter_element := element.select_one('a.chico'):
                    last_chapter = last_chapter_element.text.strip()
                else:
                    last_chapter = None

                items.append(dict(
                    slug=a_element.get('href').split('/')[-2],
                    name=unidecode.unidecode(a_element.get('title')).strip(),
                    cover=a_element.img.get('src'),
                    last_chapter=last_chapter,
                ))

            if pagination := soup.select_one('.pagination'):
                nb_pages = int(pagination.get('total'))
            else:
                nb_pages = 1

            return items, page < min(LATEST_UPDATES_RESULTS_PAGES, nb_pages)

        results = []
        delay = None
        for page in range(1, LATEST_UPDATES_RESULTS_PAGES + 1):
            if delay:
                time.sleep(delay)

            items, more = get_page(page)
            if items is not None:
                results += items
            else:
                return None

            if not more:
                break

            delay = 1

        return results

    def get_most_populars(self):
        """
        Returns most view manga list
        """
        def get_page(page):
            r = self.session_get(
                self.most_populars_url,
                params=dict(
                    f=1,
                    o=1,
                    sortby='view',
                    e='',
                )
            )
            if r.status_code != 200:
                return None, False

            soup = BeautifulSoup(r.text, 'lxml')

            items = []
            for a_element in soup.select('.pic_list .listitem a.thm-effect'):
                items.append(dict(
                    slug=a_element.get('href').split('/')[-2],
                    name=unidecode.unidecode(a_element.get('title')).strip(),
                    cover=a_element.img.get('data-src'),
                ))

            if pagination := soup.select_one('.pagination'):
                nb_pages = int(pagination.get('total'))
            else:
                nb_pages = 1

            return items, page < min(MOST_POPULAR_RESULTS_PAGES, nb_pages)

        results = []
        delay = None
        for page in range(1, MOST_POPULAR_RESULTS_PAGES + 1):
            if delay:
                time.sleep(delay)

            items, more = get_page(page)
            if items is not None:
                results += items
            else:
                return None

            if not more:
                break

            delay = 1

        return results

    def search(self, term):
        def get_page(name, page):
            r = self.session_get(self.search_url, params=dict(name=term, page=page))
            if r.status_code != 200:
                return None, False

            soup = BeautifulSoup(r.text, 'lxml')

            items = []
            for element in soup.select('#search_list li .box'):
                a_element = element.select_one('a.thm-effect')
                if last_chapter_element := element.select_one('a.chico'):
                    last_chapter = last_chapter_element.text.strip()
                else:
                    last_chapter = None

                items.append(dict(
                    slug=a_element.get('href').split('/')[-2],
                    name=unidecode.unidecode(a_element.get('title')).strip(),
                    cover=a_element.img.get('src'),
                    last_chapter=last_chapter,
                ))

            if pagination := soup.select_one('.pagination'):
                nb_pages = int(pagination.get('total'))
            else:
                nb_pages = 1

            return items, page < min(SEARCH_RESULTS_PAGES, nb_pages)

        results = []
        delay = None
        for page in range(1, SEARCH_RESULTS_PAGES + 1):
            if delay:
                time.sleep(delay)

            items, more = get_page(term, page)
            if items is not None:
                results += items
            else:
                return None

            if not more:
                break

            delay = 1

        return results
