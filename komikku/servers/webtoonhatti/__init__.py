# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara2


class Webtoonhatti(Madara2):
    id = 'webtoonhatti'
    name = 'Webtoon Hatti'
    lang = 'tr'
    is_nsfw = True

    date_format = None
    series_name = 'webtoon'

    base_url = 'https://webtoonhatti.club'
    logo_url = base_url + '/wp-content/uploads/2024/03/cropped-iconlogo.png'

    def __init__(self):
        super().__init__()
        self.session.verify = False
