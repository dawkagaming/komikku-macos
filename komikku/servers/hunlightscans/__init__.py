# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Hunlightscans(Madara):
    id = 'hunlightscans'
    name = 'Hunlight Scans'
    lang = 'en'

    base_url = 'https://hunlight.com'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'
