# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Mangaowl(Madara):
    id = 'mangaowl'
    name = 'Mangaowl'
    lang = 'en'
    is_nsfw = True

    series_name = 'read-online'  # This value changes regularly!

    base_url = 'https://mangaowl.io'
    logo_url = base_url + '/wp-content/uploads/2017/10/logo.png'
    chapters_url = base_url + '/read-online/{0}/ajax/chapters/'
