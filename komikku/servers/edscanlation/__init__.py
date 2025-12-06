# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.keyoapp import Keyoapp


class Edscanlation(Keyoapp):
    id = 'edscanlation'
    name = 'ED Scanlation'
    lang = 'fr'
    has_cf = True
    status = 'disabled'

    base_url = 'https://edscanlation.fr'
