# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Nekoscans(MangaStream):
    id = 'nekoscans'
    name = 'Neko Scans'
    lang = 'es'

    base_url = 'https://nekoproject.org'
    logo_url = 'https://i2.wp.com/nekoproject.org/wp-content/uploads/2025/12/cropped-Nekoscanlogo-1-32x32.png'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Artist") i, .tsinfo .imptdt:-soup-contains("Author") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serialization") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'
