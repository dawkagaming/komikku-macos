# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Nightscans(MangaStream):
    id = 'nightscans'
    name = 'Night scans'
    lang = 'en'

    series_name = 'series'

    base_url = 'https://nightsup.net'
    logo_url = base_url + '/wp-content/uploads/2023/03/cropped-PicsArt_09-07-01.23.08-1-2.png'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Artist") i, .tsinfo .imptdt:-soup-contains("Author") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serialization") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'
