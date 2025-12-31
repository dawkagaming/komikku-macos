# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup

from komikku.servers.multi.manga_stream import MangaStream
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type
from komikku.utils import is_number


class Carteldemanhwas(MangaStream):
    id = 'carteldemanhwas'
    name = 'Cartel De Manhwas'
    lang = 'es'
    is_nsfw = True

    chapters_order = 'desc'
    date_format: str = '%d %B, %Y'
    series_name = 'manga'

    base_url = 'https://carteldemanhwa.net'
    manga_list_url = base_url + '/cartel-de-manhwas/'

    authors_selector = '.infox .spe span:-soup-contains("Autor del Manhwa")'
    genres_selector = '[itemprop="genre"]'
    scanlators_selector = None
    status_selector = '.infox .spe span:-soup-contains("Estado")'
    synopsis_selector = '[itemprop="description"]'
    chapter_pages_selector = '.reader-area img'

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
        data['name'] = soup.select_one(self.name_selector).text.strip()

        if element := soup.select_one(self.thumbnail_selector):
            data['cover'] = element.get('src')

        # Details
        for element in soup.select(self.authors_selector):
            element.b.extract()
            if author := element.text.strip():
                data['authors'].append(author)

        for element in soup.select(self.genres_selector):
            genre = element.text.strip()
            if genre and genre not in data['genres']:
                data['genres'].append(genre)

        if element := soup.select_one('.infox .spe span:-soup-contains("Tipo")'):
            element.b.extract()
            if type_ := element.text.strip():
                data['genres'].append(type_)

        if element := soup.select_one(self.status_selector):
            element.b.extract()
            if status := element.text.strip():
                if status == 'Activo':
                    data['status'] = 'ongoing'

        if element := soup.select_one(self.synopsis_selector):
            data['synopsis'] = element.text.strip()

        # Chapters
        data['chapters'] = self.get_manga_chapters_data(soup)

        return data

    def get_manga_chapters_data(self, soup):
        chapters = []

        li_elements = soup.select('#chapter_list ul li')
        if self.chapters_order == 'desc':
            li_elements = reversed(li_elements)

        for li_element in li_elements:
            a_element = li_element.select_one('.epsleft a')

            slug = a_element.get('href').split('/')[self.slug_position]
            num = slug.split('-')[-1]
            title = a_element.text.strip()
            if date_element := li_element.select_one('.epsleft .date'):
                date = convert_date_string(date_element.text.strip(), languages=[self.lang], format=self.date_format)
            else:
                date = None

            chapters.append(dict(
                slug=slug,
                title=title,
                num=num if is_number(num) else None,
                date=date,
            ))

        return chapters

    def get_manga_list(self, title=None, type=None, orderby=None):
        r = self.session_get(
            self.manga_list_url,
            params=dict(
                status='',
                type=type,
                order=orderby or '',
                title=title,
            )
        )
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select('.relat article a'):
            name = a_element.get('title')
            cover_element = a_element.select_one('img')

            results.append(dict(
                slug=a_element.get('href').split('/')[self.slug_position],
                name=name,
                cover=cover_element.get('src') if cover_element else None,
            ))

        return results
