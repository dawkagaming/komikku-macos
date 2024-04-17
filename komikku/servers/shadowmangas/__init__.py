# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Shadowmangas(MangaStream):
    id = 'shadowmangas'
    name = 'ShadowMangas'
    lang = 'es'
    is_nsfw = True

    base_url = 'https://shadowmangas.com'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Author") i, .tsinfo .imptdt:-soup-contains("Artist") i'
    genres_selector = '.mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serialization") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'
