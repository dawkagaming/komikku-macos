# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup

from komikku.servers import Server
from komikku.utils import get_buffer_mime_type
from komikku.webview import CompleteChallenge


class Scanmanga(Server):
    id = 'scanmanga'
    name = 'Scan Manga'
    lang = 'fr'
    is_nsfw = True
    long_strip_genres = ['Webcomic', ]
    status = 'disabled'  # 2024/03 chapters and chapters images URLs have become difficult to extract (no time for that)

    has_cf = True
    http_client = 'curl_cffi'

    base_url = 'https://www.scan-manga.com'
    latest_updates_url = base_url + '/?po'
    most_populars_url = base_url + '/TOP-Manga-Webtoon-25.html'
    api_search_url = base_url + '/api/search/quick.json'
    manga_url = base_url + '{0}'
    chapter_url = base_url + '/lecture-en-ligne/{0}{1}.html'
    cover_url = 'https://cdn.scanmanga.eu/img/manga/{0}'

    def __init__(self):
        self.session = None

    @classmethod
    def get_manga_initial_data_from_url(cls, url):
        return dict(
            url=url.replace(cls.base_url, ''),
            slug=url.split('/')[-1].replace('.html', ''),
        )

    @CompleteChallenge()
    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's relative url and slug (provided by search)
        """
        assert 'url' in initial_data and 'slug' in initial_data, 'Manga url or slug are missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['url']))
        if r.status_code != 200:
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

        data['name'] = soup.find('div', class_='h2_titre').h2.text.strip()
        if data.get('cover') is None:
            data['cover'] = soup.find('div', class_='image_manga').img.get('src')

        # Details
        li_elements = soup.find('div', class_='contenu_texte_fiche_technique').find_all('li')
        for a_element in li_elements[0].find_all('a'):
            data['authors'].append(a_element.text.strip())

        data['genres'] = [g.strip() for g in li_elements[1].text.split()]
        for a_element in li_elements[2].find_all('a'):
            a_element.span.extract()
            data['genres'].append(a_element.text.strip())

        status = li_elements[6].text.strip().lower()
        if status == 'en cours':
            data['status'] = 'ongoing'
        elif status in ('one shot', 'terminé'):
            data['status'] = 'complete'
        elif status == 'en pause':
            data['status'] = 'hiatus'

        for a_element in li_elements[7].find_all('a'):
            data['scanlators'].append(a_element.text.strip())

        # Synopsis
        p_element = soup.find('div', class_='texte_synopsis_manga').find('p', itemprop='description')
        p_element.span.extract()
        data['synopsis'] = p_element.text.strip()

        # Chapters
        for element in reversed(soup.select('.chapitre_nom')):
            a_element = element.a
            if not a_element or element.select_one('.typcn-lock-closed') or element.select_one('.typcn-lock-open'):
                # Skip external chapters
                continue

            data['chapters'].append(dict(
                slug=a_element.get('href').split('/')[-1].replace(data['slug'], '').replace('.html', ''),
                title=element.text.strip(),
                date=None,
            ))

        return data

    @CompleteChallenge()
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

        for script_element in soup.find_all('script'):
            script = script_element.string
            if not script or 'var nPa = new Array' not in script:
                continue

            image_base_url = None
            for line in script.split('\n'):
                line = line.strip()

                if 'var nPa = new Array' in line:
                    array_name = line.split(' ')[1]

                    for item in line.split(';'):
                        if not item.startswith(f'{array_name}['):
                            continue

                        data['pages'].append(dict(
                            slug=None,
                            image=item.split('"')[1],
                        ))

                elif line.startswith(('tlo =', "$('#preload')")):
                    image_base_url = line.split("'")[-2]
                    break

            if image_base_url:
                for page in data['pages']:
                    page['image'] = image_base_url + page['image']

            break

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        self.create_session()  # Session must be refreshed each time

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
            name=page['image'].split('?')[0].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(url)

    @CompleteChallenge()
    def get_latest_updates(self):
        """
        Returns latest updates
        """
        r = self.session_get(self.latest_updates_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select('#content_news .nom_manga'):
            name = a_element.text.strip()
            if 'Novel' in name:
                continue

            results.append(dict(
                name=name,
                slug=a_element.get('href').split('/')[-1].replace('.html', ''),
                url=a_element.get('href').replace(self.base_url, ''),
            ))

        return results

    @CompleteChallenge()
    def get_most_populars(self):
        """
        Returns list of top manga
        """
        r = self.session_get(self.most_populars_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for cover_element in soup.select('.image_manga'):
            element = cover_element.find_next_siblings()[0]

            a_element = element.h3.a
            name = a_element.text.strip()
            if 'Novel' in name:
                # Skip
                continue

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1].replace('.html', ''),
                url=a_element.get('href').replace(self.base_url, ''),
                cover=cover_element.select_one('img').get('data-original'),
            ))

        return results

    @CompleteChallenge()
    def search(self, term):
        r = self.session_get(
            self.api_search_url,
            params=dict(term=term),
            default_headers=True,
            headers={
                'Accept': '*/*',
                'Content-Type': 'application/json; charset=UTF-8',
                'Referer': f'{self.base_url}/',
            }
        )

        if r.status_code == 200:
            try:
                data = r.json()
                results = []
                for item in data['title']:
                    if item['type'] == 'Novel':
                        # Skip
                        continue

                    results.append(dict(
                        url=item['url'],
                        slug=item['url'].split('/')[-1].replace('.html', ''),
                        name=item['nom_match'],
                        cover=self.cover_url.format(item['image']),
                        last_chapter=str(item['l_ch']),
                    ))
            except Exception:
                return None
            else:
                return results

        return None
