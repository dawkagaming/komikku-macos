# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.pizzareader import PizzaReader


class Bluesolo(PizzaReader):
    id = 'bluesolo'
    name = 'Blue Solo'
    lang = 'fr'

    base_url = 'https://bluesolo.org'
    logo_url = base_url + '/storage/img/logo/Logo copie-72.png'
