# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Mangacrab(Madara):
    id = 'mangacrab'
    name = 'MangaCrab'
    lang = 'es'
    is_nsfw = True

    date_format = '%d/%m/%Y'
    series_name = 'series'

    base_url = 'https://visorcrab.com'

    details_name_selector = '.titulodetalles'
    details_cover_selector = '#miniatura > a > img'
    details_scanlators_selector = '.post-content_item:-soup-contains("Scanlation") .summary-content'
    details_status_selector = '.post-content_item:-soup-contains("Estado") .summary-content2'
    details_synopsis_selector = '.sinopsis-completa'
    chapters_selector = '.lista-de-capitulos'
