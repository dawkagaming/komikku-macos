# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.my_manga_reader_cms import MyMangaReaderCMS

# Clone of https://mangascan-fr.co


class Bentoscan(MyMangaReaderCMS):
    id = 'bentoscan'
    name = 'Bentoscan'
    lang = 'fr'
    status = 'disabled'

    base_url = 'https://bentoscan.com'
    search_url = base_url + '/search'
    most_populars_url = base_url + '/filterList?page=1&cat=&alpha=&sortBy=views&asc=false&author=&tag=&artist='
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'
    image_url = None  # images all seem to come from a different server (scansmangas.me)
    cover_url = base_url + '/uploads/manga/{0}.jpg'

    details_name_selector = 'h2.widget-title'
