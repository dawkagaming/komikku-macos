# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.peachscan import Peachscan


class Dangoscan(Peachscan):
    id = 'dangoscan'
    name = 'Dango Scan'
    lang = 'pt_BR'

    base_url = 'https://dangoscan.com.br'
