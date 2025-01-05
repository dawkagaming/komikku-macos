# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.peachscan import Peachscan


class Nazarickscan(Peachscan):
    id = 'nazarickscan'
    name = 'Nazarick Scan'
    lang = 'pt_BR'

    base_url = 'https://nazarickscan.com.br'
