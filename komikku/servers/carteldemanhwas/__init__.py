# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Carteldemanhwas(MangaStream):
    id = 'carteldemanhwas'
    name = 'Cartel De Manhwas'
    lang = 'es'
    is_nsfw = True

    chapters_order = 'asc'
    series_name = 'series'

    base_url = 'https://carteldemanhwas.com'

    authors_selector = '.infotable tr:-soup-contains("Artist") td:last-child, .infotable tr:-soup-contains("Author") td:last-child'
    genres_selector = '.seriestugenre a'
    scanlators_selector = None
    status_selector = '.seriestucontent table tr:-soup-contains("Status") td:last-child'
    synopsis_selector = '[itemprop="description"]'
