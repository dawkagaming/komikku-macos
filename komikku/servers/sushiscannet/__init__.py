# SPDX-FileCopyrightText: 2025-2025 Lélahel Hideux
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Lélahel Hideux <lelahx@proton.me>

from komikku.servers.multi.manga_stream import MangaStream


class Sushiscannet(MangaStream):
    id = 'sushiscannet'
    name = 'SushiScanNet'
    lang = 'fr'

    has_cf = True

    base_url = 'https://sushiscan.net'

    series_name = 'catalogue'

    authors_selector = '.infotable tr:-soup-contains("Dessinateur") td:last-child, .infotable tr:-soup-contains("Auteur") td:last-child'
    genres_selector = '.seriestugenre a'
    scanlators_selector = None
    status_selector = '.infotable tr:-soup-contains("Statut") td:last-child'
    synopsis_selector = '[itemprop="description"]'
