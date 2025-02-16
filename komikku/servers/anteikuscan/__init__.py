# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.keyoapp import Keyoapp


class Anteikuscan(Keyoapp):
    id = 'anteikuscan'
    name = 'Anteiku Scans'
    lang = 'fr'
    is_nsfw = True
    has_cf = True

    base_url = 'https://anteikuscan.fr'
