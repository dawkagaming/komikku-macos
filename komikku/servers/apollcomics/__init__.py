# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Apollcomics(Madara):
    id = 'apollcomics'
    name = 'Apoll Comics'
    lang = 'es'
    is_nsfw = True

    base_url = 'https://apollcomics.es'
    logo_url = base_url + '/wp-content/uploads/2022/02/cropped-assda-32x32.png'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'
