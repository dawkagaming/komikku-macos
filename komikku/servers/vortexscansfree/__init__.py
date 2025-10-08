# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Vortexscansfree(MangaStream):
    id = 'vortexscansfree'
    name = 'Vortex Scans For Free'
    lang = 'en'
    status = 'disabled'

    base_url = 'https://vortexscansfree.com'
    logo_url = base_url + '/wp-content/uploads/2024/12/cropped-Logo-d426c8cb30892710-32x32.webp'

    series_name = 'manga'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Artist") i, .tsinfo .imptdt:-soup-contains("Author") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serialization") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'
