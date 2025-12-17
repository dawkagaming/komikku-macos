# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.heancms import HeanCMS


class Ezmanga(HeanCMS):
    id = 'ezmanga'
    name = 'EZmanga'
    lang = 'en'

    base_url = 'https://ezmanga.org'
    api_url = 'https://vapi.ezmanga.org/api'
