# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Tecnoscan(MangaStream):
    id = 'tecnoscan'
    name = 'Tecno Scan'
    lang = 'es'

    base_url = 'https://visortecno.com'

    authors_selector = '.infox .fmed:-soup-contains("Artista") span, .infox .fmed:-soup-contains("Autor") span'
    genres_selector = '.infox .mgen a'
    scanlators_selector = '.infox .fmed:-soup-contains("Serialización") span'
    status_selector = '.tsinfo .imptdt:-soup-contains("Estado") i'
    synopsis_selector = '[itemprop="description"]'
