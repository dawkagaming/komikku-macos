# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# Supported servers:
# JManga [JA] (disabled)
# Read Comics Free [EN] (disabled)
# Xoxocomics [EN]

from bs4 import BeautifulSoup
import requests
from urllib.parse import parse_qs
from urllib.parse import urlparse

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_soup_element_inner_text
from komikku.utils import get_buffer_mime_type
from komikku.utils import is_number

# WPComics Wordpress theme


class WPComics(Server):
    base_url: str = None
    search_url: str = None
    latest_updates_url: str = None
    most_populars_url: str = None
    manga_url: str = None
    chapter_url: str = None

    date_format: str = '%m/%d/%Y'
    ignore_images_status_code: bool = False

    details_name_selector: str = None
    details_cover_selector: str = None
    details_status_selector: str = None
    details_authors_selector: str = None
    details_genres_selector: str = None
    details_synopsis_selector: str = None
    results_link_selector: str = None
    results_cover_img_selector: str = None
    results_last_chapter_link_selector: str = None
    results_last_chapter_lastest_updates_link_selector: str = None

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

        data['name'] = soup.select_one(self.details_name_selector).text.strip()
        data['cover'] = soup.select_one(self.details_cover_selector).get('src')

        status = soup.select_one(self.details_status_selector).text.strip().lower()
        if status in ('completed', '完結済み'):
            data['status'] = 'complete'
        elif status in ('ongoing', '連載中'):
            data['status'] = 'ongoing'

        if elements := soup.select(self.details_authors_selector):
            for element in elements:
                # elements can be <a> or <p>
                if element.name == 'p':
                    for author in element.text.strip().split(' - '):
                        data['authors'].append(author.strip())
                else:
                    data['authors'].append(element.text.strip())

        if a_elements := soup.select(self.details_genres_selector):
            for a_element in a_elements:
                data['genres'].append(a_element.text.strip())

        if element := soup.select_one(self.details_synopsis_selector):
            data['synopsis'] = get_soup_element_inner_text(element, recursive=False)

        # Chapters
        def walk_chapters_pages(num=None, soup=None):
            if soup is None and num is not None:
                r = self.session_get(self.manga_url.format(initial_data['slug']), params=dict(page=num))
                if r.status_code != 200:
                    return None

                mime_type = get_buffer_mime_type(r.content)
                if mime_type != 'text/html':
                    return None

                soup = BeautifulSoup(r.text, 'lxml')

            for li_element in soup.select('#nt_listchapter ul li.row'):
                if 'heading' in li_element.get('class'):
                    continue

                a_element = li_element.select_one('div a')
                slug = a_element.get('href').split('/')[-1]
                num = slug.split('-')[-1] if slug.startswith('issue-') else None
                date = li_element.select_one('div:last-child').text.strip()

                data['chapters'].append(dict(
                    slug=a_element.get('href').split('/')[-1],
                    title=a_element.text.replace(data['name'], '').strip(),
                    num=num if is_number(num) else None,
                    date=convert_date_string(date, self.date_format),
                ))

            if next_element := soup.select_one('a[rel="next"]'):
                next_url = next_element.get('href')
                next_num = parse_qs(urlparse(next_url).query)['page'][0]
                walk_chapters_pages(num=next_num)

        walk_chapters_pages(soup=soup)
        data['chapters'] = list(reversed(data['chapters']))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns comic chapter data

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
        for index, img_element in enumerate(soup.select('.page-chapter > img')):
            data['pages'].append(dict(
                slug=None,
                image=img_element.get('data-original'),
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
        if r.status_code != 200 and not self.ignore_images_status_code:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=f'{page["index"]:04d}.{mime_type.split("/")[-1]}' if page.get('index') else page['image'].split('/')[-1],  # noqa E231
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
        for element in soup.select('.list-chapter .row'):
            a_element = element.select_one(self.results_link_selector)
            img_element = element.select_one(self.results_cover_img_selector)
            last_a_element = element.select_one(self.results_last_chapter_lastest_updates_link_selector)

            name = a_element.text.strip()

            results.append(dict(
                name=name,
                slug=a_element.get('href').split('/')[-1],
                cover=img_element.get('data-original'),
                last_chapter=last_a_element.text.replace(name, '').replace('Issue', '').strip() if last_a_element else None,
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
        for element in soup.select('.items .item'):
            a_element = element.select_one(self.results_link_selector)
            img_element = element.select_one(self.results_cover_img_selector)
            last_a_element = element.select_one(self.results_last_chapter_link_selector)

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
                cover=img_element.get('data-original'),
                last_chapter=last_a_element.text.replace('Issue', '').strip() if last_a_element else None,
            ))

        return results

    def search(self, term):
        r = self.session.get(
            self.search_url,
            params=dict(
                keyword=term,
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
        for element in soup.select('.items .item'):
            a_element = element.select_one(self.results_link_selector)
            img_element = element.select_one(self.results_cover_img_selector)
            last_a_element = element.select_one(self.results_last_chapter_link_selector)

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
                cover=img_element.get('data-original'),
                last_chapter=last_a_element.text.replace('Issue', '').strip() if last_a_element else None,
            ))

        return results
