# Copyright (C) 2020-2024 Liliana Prikler
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Liliana Prikler <liliana.prikler@gmail.com>

from bs4 import BeautifulSoup
import json

from komikku.servers import Server
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type
from komikku.webview import BypassCF

IMAGES_EXTS = dict(g='gif', j='jpg', p='png')


class Nhentai(Server):
    id = 'nhentai'
    name = 'NHentai'
    lang = 'en'
    lang_code = 'english'
    is_nsfw_only = True

    has_cf = True

    base_url = 'https://nhentai.net'
    search_url = base_url + '/search'
    manga_url = base_url + '/g/{0}'
    page_image_url = 'https://i.nhentai.net/galleries/{0}/{1}'

    @BypassCF()
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

        title = soup.find('meta', property='og:title')['content']
        image_url = soup.find('meta', property='og:image')['content']
        all_tags = soup.find('meta', property='og:description')['content']
        tags = [t.strip() for t in all_tags.split(',')]

        data = initial_data.copy()
        data.update(dict(
            name=title,
            cover=image_url,
            authors=[],
            scanlators=[],
            genres=tags,
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        info = soup.find('div', id='info')
        data['chapters'].append(dict(
           slug=image_url.rstrip('/').split('/')[-2],
           title=title,
        ))

        for tag_container in info.select('#tags .tag-container'):
            category = tag_container.text.split(':')[0].strip()

            if category == 'Uploaded':
                time = tag_container.find('time').get('datetime')
                data['chapters'][0]['date'] = convert_date_string(time.split('T')[0], '%Y-%m-%d')

            for tag in tag_container.select('.tag'):
                clean_tag = tag.select_one('span.name').text.strip()
                if category in ['Artists', 'Groups', ]:
                    data['authors'].append(clean_tag)
                if category in ['Tags', ]:
                    data['genres'].append(clean_tag)

        return data

    @BypassCF()
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.manga_url.format(manga_slug))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        pages = []
        for script_element in soup.find_all('script'):
            script = script_element.string
            if not script or not script.strip().startswith('window._gallery'):
                continue

            info = json.loads(script.strip().split('\n')[0][30:-3].replace('\\u0022', '"').replace('\\u005C', '\\'))
            if not info.get('images') or not info['images'].get('pages'):
                break

            for index, page in enumerate(info['images']['pages']):
                num = index + 1
                extension = IMAGES_EXTS[page['t']]
                page = dict(
                    image=None,
                    slug=f'{num}.{extension}',
                )
                pages.append(page)

        return dict(pages=pages)

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        assert chapter_slug is not None
        r = self.session_get(self.page_image_url.format(chapter_slug, page['slug']))
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

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def _search_common(self, params):
        r = self.session_get(self.search_url, params=params)

        if r.status_code == 200:
            try:
                results = []
                soup = BeautifulSoup(r.text, 'lxml')
                elements = soup.find_all('div', class_='gallery')

                for element in elements:
                    a_element = element.find('a', class_='cover')
                    caption_element = element.find('div', class_='caption')
                    results.append(dict(
                        slug=a_element.get('href').rstrip('/').split('/')[-1],
                        name=caption_element.text.strip(),
                        cover=a_element.img.get('data-src'),
                    ))
            except Exception:
                return None
            else:
                return results

        return None

    @BypassCF()
    def get_most_populars(self):
        """
        Returns most popular mangas (bayesian rating)
        """
        return self._search_common({'q': 'language:' + self.lang_code, 'sort': 'popular'})

    @BypassCF()
    def search(self, term):
        term = term + ' language:' + self.lang_code
        return self._search_common({'q': term})


class Nhentai_chinese(Nhentai):
    id = 'nhentai_chinese'
    lang = 'zh_Hans'
    lang_code = 'chinese'


class Nhentai_japanese(Nhentai):
    id = 'nhentai_japanese'
    lang = 'ja'
    lang_code = 'japanese'
