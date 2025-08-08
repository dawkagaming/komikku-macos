# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup

from komikku.servers.multi.madara import Madara2


class Mangacrab(Madara2):
    id = 'mangacrab'
    name = 'MangaCrab'
    lang = 'es'
    is_nsfw = True

    date_format = '%d/%m/%Y'
    series_name = 'series'

    base_url = 'https://mangacrab.topmanhuas.org'
    logo_url = base_url + '/wp-content/uploads/2017/10/cropped-logo100-Personalizado-32x32.png'
    chapters_url = base_url + '/series/{0}/ajax/chapters/'

    details_name_selector = 'h1.post-title'
    details_status_selector = '.post-content_item:-soup-contains("Estado") .summary-content'

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(
            self.chapter_url.format(manga_slug, chapter_slug),
            headers={
                'Referer': self.manga_url.format(manga_slug),
            }
        )
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        index = 1
        for img_element in soup.select('.reading-content img.wp-manga-chapter-img'):
            image = None
            for attr, value in img_element.attrs.items():
                if attr.startswith('data-img-'):
                    image = value.strip()
                    break
            if image is None:
                continue

            data['pages'].append(dict(
                slug=None,
                image=image,
                index=index,
            ))
            index += 1

        return data

    def search(self, term, nsfw, orderby=None):
        params = {
            's': term or '',
            'post_type': 'wp-manga',
            'type': 'manga',
        }

        if orderby == 'populars':
            params['m_orderby'] = 'views'
        elif orderby == 'latest':
            params['m_orderby'] = 'latest'

        r = self.session_get(f'{self.base_url}/', params=params)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.select('.search-lists .manga__item'):
            a_element = element.select_one('.post-title h2 a')
            thumb_element = element.select_one('.manga__thumb_item')
            nb_chapters_element = element.select_one('.manga-info .total')

            if cover_element := thumb_element.a.img or element.img:
                cover = cover_element.get('data-src')
                if not cover:
                    cover = cover_element.get('src')
            else:
                cover = None

            results.append(dict(
                slug=a_element.get('href').split('/')[-2],
                name=a_element.text.strip(),
                cover=cover,
                nb_chapters=nb_chapters_element.text.strip().split()[0] if nb_chapters_element else None,
            ))

        return results
