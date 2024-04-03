# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup

from komikku.servers.multi.wpcomics import Wpcomics
from komikku.servers.utils import get_buffer_mime_type


class Jmanga(Wpcomics):
    id = 'jmanga'
    name = 'JManga'
    lang = 'ja'
    is_nsfw = True

    base_url = 'https://jmanga.vip'
    search_url = base_url + '/search/manga'
    latest_updates_url = base_url + '/search/manga?status=-1'
    most_populars_url = base_url + '/search/manga?status=-1&sort=11'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'

    details_name_selector = '.breadcrumb li:last-child span'
    details_cover_selector = '#item-detail .col-image img'
    details_status_selector = '#item-detail .list-info .status p:last-child'
    details_authors_selector = '#item-detail .list-info .author p:last-child'
    details_genres_selector = '#item-detail .list-info .kind p:last-child a'
    details_synopsis_selector = '#item-detail .detail-content'
    results_link_selector = 'h3 a'
    results_cover_img_selector = '.box_img a img'
    results_last_chapter_link_selector = '.comic-item .chapter a'
    results_last_chapter_lastest_updates_link_selector = '.hlb-list li a'

    def get_latest_updates(self):
        """
        Returns latest updates

        Contrary to the standard WPComics theme, there is no latest updates dedicated page, so we use search instead.
        """
        r = self.session.get(
            self.latest_updates_url,
            headers={
                'Referer': self.search_url,
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
