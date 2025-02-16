# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Atikrost(Madara):
    id = 'atikrost'
    name = 'Atikrost'
    lang = 'tr'
    status = 'disabled'

    date_format = None

    base_url = 'https://www.mangaoku.org'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'
