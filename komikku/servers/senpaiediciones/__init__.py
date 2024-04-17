# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Senpaiediciones(MangaStream):
    id = 'senpaiediciones'
    name = 'Senpai Ediciones'
    lang = 'es'
    is_nsfw = True

    base_url = 'https://senpaiediciones.com'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Autor") i, .tsinfo .imptdt:-soup-contains("Artista") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serializado por") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Estado") i'
    synopsis_selector = '[itemprop="description"]'

    chapter_pages_selector = '#readerarea img.lazyload'
