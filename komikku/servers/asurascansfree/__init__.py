# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Asurascansfree(MangaStream):
    id = 'asurascansfree'
    name = 'Asura Scans For Free'
    lang = 'en'
    status = 'disabled'

    base_url = 'https://asurascansfree.com'
    logo_url = base_url + '/wp-content/uploads/2024/12/cropped-Asura-scans-free-icon-32x32.png'

    series_name = 'serie'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Artist") i, .tsinfo .imptdt:-soup-contains("Author") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serialization") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'
