# Copyright (C) 2019-2025 Valéry Febvre
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

    base_url = 'https://toonscrab.com'

    details_name_selector = '.post-title > h1'
