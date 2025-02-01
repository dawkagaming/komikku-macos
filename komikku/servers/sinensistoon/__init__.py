# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.peachscan import Peachscan

# 2025/01 fusion of Sinensis and Cerise => SCtoon


class Sinensistoon(Peachscan):
    id = 'sinensistoon'
    name = 'SCtoon'
    lang = 'pt_BR'
    has_cf = True

    base_url = 'https://sctoon.net'
