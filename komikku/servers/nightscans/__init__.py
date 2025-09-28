# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import logging

from komikku.servers.multi.heancms import HeanCMS

logger = logging.getLogger(__name__)


class Nightscans(HeanCMS):
    id = 'nightscans'
    name = 'Qi Scans (Night scans)'
    lang = 'en'
    has_cf = True

    base_url = 'https://qiscans.org'
    api_url = 'https://api.qiscans.org/api'
    bypass_cf_url = base_url + '/series'
