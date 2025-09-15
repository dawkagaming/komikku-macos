# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import logging

from komikku.servers.multi.heancms import HeanCMS

logger = logging.getLogger(__name__)


class Ezmanga(HeanCMS):
    id = 'ezmanga'
    name = 'EZmanga'
    lang = 'en'
    has_cf = True

    base_url = 'https://ezmanga.org'
    api_url = 'https://vapi.ezmanga.org/api'
