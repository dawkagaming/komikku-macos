# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.peachscan import Peachscan


class Luratoonscan(Peachscan):
    id = 'luratoonscan'
    name = 'Luratoon Scan'
    lang = 'pt_BR'

    has_cf = True

    base_url = 'https://luratoons.com'
