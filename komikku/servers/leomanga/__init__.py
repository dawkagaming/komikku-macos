# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara2


class Leomanga(Madara2):
    id = 'leomanga'
    name = 'Lectormanga (Leomanga)'
    lang = 'es'
    is_nsfw = True
    has_cf = True

    series_name = 'biblioteca'

    base_url = 'https://lectormangaa.com'
