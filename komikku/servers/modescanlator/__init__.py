# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.heancms import HeanCMS


class Modescanlator(HeanCMS):
    id = 'modescanlator'
    name = 'Mode Scanlator'
    lang = 'pt_BR'

    base_url = 'https://modescanlator.com'
    api_url = 'https://api.modescanlator.com'

    cover_css_path = '#content div.container:first-child > div > div:last-child img'
    authors_css_path = 'div.flex:-soup-contains("Author") > span:last-child'
    synopsis_css_path = 'div.text-muted-foreground > div:nth-child(1)'
