# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Sushiscan(MangaStream):
    id = 'sushiscan'
    name = 'SushiScan'
    lang = 'fr'

    has_cf = True

    base_url = 'https://sushiscan.fr'

    series_name = 'catalogue'

    authors_selector = '.infotable tr:-soup-contains("Dessinateur") td:last-child, .infotable tr:-soup-contains("Auteur") td:last-child'
    genres_selector = '.seriestugenre a'
    scanlators_selector = None
    status_selector = '.infotable tr:-soup-contains("Statut") td:last-child'
    synopsis_selector = '[itemprop="description"]'
