# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Tecnoscan(MangaStream):
    id = 'tecnoscan'
    name = 'Terco Scans (Tecno Scans)'
    lang = 'en'

    base_url = 'https://terco-dooms.xyz'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Artist") i, .tsinfo .imptdt:-soup-contains("Author") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serialization") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'
