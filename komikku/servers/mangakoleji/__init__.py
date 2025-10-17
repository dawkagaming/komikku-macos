# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Mangakoleji(MangaStream):
    id = 'mangakoleji'
    name = 'Manga Koleji'
    lang = 'tr'
    status = 'disabled'

    base_url = 'https://mangakoleji.com'
    logo_url = base_url + '/wp-content/uploads/2024/08/cropped-manga-koleji-com-32x32.png'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Çizer") i, .tsinfo .imptdt:-soup-contains("Yazar") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Yayınlayan") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Durum") i'
    synopsis_selector = '[itemprop="description"]'
