# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Webtoontr(Madara):
    id = 'webtoontr'
    name = 'Webtoon TR'
    lang = 'tr'
    is_nsfw = True

    date_format = '%d/%m/%Y'
    series_name = 'webtoon'

    base_url = 'https://webtoontr.net'
    chapter_url = base_url + '/' + series_name + '/{0}/{1}/'

    details_synopsis_selector = '.manga-excerpt'
