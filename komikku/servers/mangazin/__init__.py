# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Mangazin(Madara):
    id = 'mangazin'
    name = 'MangaZin'
    lang = 'en'
    is_nsfw = True

    base_url = 'https://mangazin.org'
