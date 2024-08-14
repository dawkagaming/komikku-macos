# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.keyoapp import Keyoapp


class Anteikuscan(Keyoapp):
    id = 'anteikuscan'
    name = 'Anteiku Scans'
    lang = 'fr'
    is_nsfw = True

    base_url = 'https://anteikuscan.fr'
