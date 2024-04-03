# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.wpcomics import Wpcomics


class Xoxocomics(Wpcomics):
    id = 'xoxocomics'
    name = 'Xoxocomics'
    lang = 'en'
    is_nsfw = True

    base_url = 'https://xoxocomic.com'
    search_url = base_url + '/search-comic'
    latest_updates_url = base_url + '/comic-update'
    most_populars_url = base_url + '/popular-comic'
    manga_url = base_url + '/comic/{0}'
    chapter_url = base_url + '/comic/{0}/{1}/all'

    details_name_selector = '.breadcrumb li:last-child span'
    details_cover_selector = '#item-detail .col-image img'
    details_status_selector = '#item-detail .list-info .status p:last-child'
    details_authors_selector = '#item-detail .list-info .author p:last-child'
    details_genres_selector = '#item-detail .list-info .kind p:last-child a'
    details_synopsis_selector = '#item-detail .detail-content p'
    results_link_selector = 'h3 a'
    results_cover_img_selector = '.box_img a img'
    results_last_chapter_link_selector = 'figcaption ul li a'
    results_last_chapter_lastest_updates_link_selector = '.hlb-list li a'
