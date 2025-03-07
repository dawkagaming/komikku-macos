# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Webtoonhatti(Madara):
    id = 'webtoonhatti'
    name = 'Webtoon Hatti'
    lang = 'tr'
    is_nsfw = True

    date_format = None
    series_name = 'webtoon'

    base_url = 'https://webtoonhatti.me'
    logo_url = base_url + '/wp-content/uploads/2024/03/cropped-iconlogo.png'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'
