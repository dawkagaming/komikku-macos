# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara2


class Mangaweebs(Madara2):
    id = 'mangaweebs'
    name = 'MangaWeebs'
    lang = 'en'
    is_nsfw = True
    status = 'disabled'

    date_format = None  # broken, year is missing!

    # mirror: https://ns2.mangaweebs.in

    base_url = 'https://mangaweebs.in'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'
