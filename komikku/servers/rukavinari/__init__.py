# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Rukavinari(MangaStream):
    id = 'rukavinari'
    name = 'Rukav Inari'
    lang = 'es'
    is_nsfw = True
    status = 'disabled'

    slug_position = -1

    base_url = 'https://rukavinari.org'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Autor") i, .tsinfo .imptdt:-soup-contains("Artista") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serialización") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Estado") i'
    synopsis_selector = '[itemprop="description"]'
