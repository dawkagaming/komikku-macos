# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Mangalek(Madara):
    id = 'mangalek'
    name = 'مانجا ليك Mangalek'
    lang = 'ar'

    date_format = '%Y ,%d %B'

    base_url = 'https://lekmanga.net'
    logo_url = 'https://io.lekmanga.net/wp-content/uploads/2020/05/cropped-%D9%85%D8%A7%D9%86%D8%AC%D8%A7-%D9%84%D9%8A%D9%83-1-300x114-1-32x32.png'
    chapter_url = base_url + '/manga/{0}/{1}/'

    # Mirrors
    # https://lekmanga.org
    # https://lekmanga.com
    # https://like-manga.net
    # https://manga-leko.org
