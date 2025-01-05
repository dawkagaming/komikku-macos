# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Vfscan(MangaStream):
    id = 'vfscan'
    name = 'VF Scan'
    lang = 'fr'
    status = 'disabled'

    base_url = 'https://www.vfscan.net'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Mangaka") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = None
    status_selector = '.tsinfo .imptdt:-soup-contains("Statut") i'
    synopsis_selector = '[itemprop="description"]'
