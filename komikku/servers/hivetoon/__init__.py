# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.heancms import HeanCMS


class Hivetoon(HeanCMS):
    id = 'hivetoon'
    name = 'Hive Toon'
    lang = 'en'

    base_url = 'https://hivetoons.org'
    logo_url = 'https://storage.hivetoon.com/public/upload/2024/12/05/logo-end-1 (1)-09f57d7d7ea3f031.webp'
    api_url = 'https://api.hivetoons.org/api'
