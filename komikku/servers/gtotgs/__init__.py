# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.pizzareader import PizzaReader


class Gtotgs(PizzaReader):
    id = 'gtotgs'
    name = 'GTO TGS'
    lang = 'it'
    is_nsfw = True

    base_url = 'https://reader.gtothegreatsite.net'
    logo_url = base_url + '/storage/img/logo/gto-tgs-logo-72.png'
