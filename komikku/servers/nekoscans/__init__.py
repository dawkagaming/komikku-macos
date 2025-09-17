# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Nekoscans(MangaStream):
    id = 'nekoscans'
    name = 'Neko Scans'
    lang = 'es'
    status = 'disabled'

    is_nsfw = True

    base_url = 'https://nekoscans.org'
    logo_url = 'https://i1.wp.com/nekoscans.org/wp-content/uploads/2025/05/cropped-Nekoscanlogo-32x32.png'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Artist") i, .tsinfo .imptdt:-soup-contains("Author") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Serialization") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'
