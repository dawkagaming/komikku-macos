# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Poseidonscans(Madara):
    id = 'poseidonscans'
    name = 'Poseidon Scans'
    lang = 'fr'
    is_nsfw = True

    has_cf = True

    date_format = None

    base_url = 'https://poseidonscans.fr'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'
