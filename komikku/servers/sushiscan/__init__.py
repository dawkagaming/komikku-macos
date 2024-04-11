# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Sushiscan(MangaStream):
    id = 'sushiscan'
    name = 'SushiScan'
    lang = 'fr'

    base_url = 'https://sushiscan.fr'

    authors_selector = '.infotable tr:-soup-contains("Artiste") td:last-child, .infotable tr:-soup-contains("Auteur") td:last-child'
    genres_selector = '.seriestugenre a'
    scanlators_selector = None
    status_selector = '.seriestucontent table tr:-soup-contains("Statut") td:last-child'
    synopsis_selector = '[itemprop="description"]'
