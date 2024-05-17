# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.peachscan import Peachscan


class Dangoscan(Peachscan):
    id = 'dangoscan'
    name = 'Dango Scan'
    lang = 'pt_BR'

    base_url = 'https://dangoscan.com.br'
