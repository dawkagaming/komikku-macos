# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.heancms import HeanCMS


class Hijalascans(HeanCMS):
    id = 'hijalascans'
    name = 'Hijala Scans'
    lang = 'en'

    base_url = 'https://en-hijala.com'
    logo_url = 'https://storage.en-hijala.com/upload/2025/06/24/final-523b7e2e4fb3a659.webp'
    api_url = 'https://api.en-hijala.com/api'
