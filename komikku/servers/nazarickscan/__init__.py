# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.peachscan import Peachscan


class Nazarickscan(Peachscan):
    id = 'nazarickscan'
    name = 'Nazarick Scan'
    lang = 'pt_BR'
    status = 'disabled'

    base_url = 'https://nazarickscan.com.br'
    logo_url = base_url + '/static/nazarickscan.com.br/favicon-32x32.png'
