# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.keyoapp import Keyoapp


class Ezmanga(Keyoapp):
    id = 'ezmanga'
    name = 'EZmanga'
    lang = 'en'
    has_cf = True

    base_url = 'https://ezmanga.org'
