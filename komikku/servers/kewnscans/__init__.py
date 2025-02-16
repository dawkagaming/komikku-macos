# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.keyoapp import Keyoapp


class Kewnscans(Keyoapp):
    id = 'kewnscans'
    name = 'Kewn Scans'
    lang = 'en'

    base_url = 'https://kewnscans.org'
