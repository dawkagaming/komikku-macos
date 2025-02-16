# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.peachscan import Peachscan


class Cerisescan(Peachscan):
    id = 'cerisescan'
    name = 'Cerise Scan'
    lang = 'pt_BR'
    status = 'disabled'  # 2025/01 fusion of Cerise and Sinensis and Cerise => SCtoon

    has_cf = True

    base_url = 'https://cerise.leitorweb.com'
