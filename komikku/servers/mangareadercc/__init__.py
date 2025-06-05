# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.paprika import Paprika


class Mangareadercc(Paprika):
    id = 'mangareadercc'
    name = 'MangaReader (cc)'
    lang = 'en'

    has_cf = True
    is_nsfw = True

    base_url = 'https://mangareader.in'
    logo_url = base_url + '/frontend/imgs/favicon16.png'
    bypass_cf_url = base_url + '/manga/selena'
