# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Ryujinmanga(MangaStream):
    id = 'ryujinmanga'
    name = 'Ryujinmanga'
    lang = 'es'

    base_url = 'https://www.ryujinmanga.com'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Autor") i, .tsinfo .imptdt:-soup-contains("Artista") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Publicado en") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Estado") i'
    synopsis_selector = '[itemprop="description"]'
