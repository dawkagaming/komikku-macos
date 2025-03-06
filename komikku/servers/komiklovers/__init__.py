# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Komiklovers(MangaStream):
    id = 'komiklovers'
    name = 'KomikLovers'
    lang = 'id'

    series_name = 'komik'

    base_url = 'https://komiklovers.com'
    logo_url = 'https://i1.wp.com/komiklovers.com/wp-content/uploads/2024/05/cropped-SAVE_20240527_203449-32x32.jpg'

    authors_selector = '.infotable tr:-soup-contains("Artist") td:last-child, .infotable tr:-soup-contains("Author") td:last-child'
    genres_selector = '.seriestugenre a'
    scanlators_selector = None
    status_selector = '.seriestucontent table tr:-soup-contains("Status") td:last-child'
    synopsis_selector = '[itemprop="description"]'
