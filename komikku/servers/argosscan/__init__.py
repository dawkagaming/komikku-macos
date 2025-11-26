# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara2


class Argosscan(Madara2):
    id = 'argosscan'
    name = 'Argos Comics'
    lang = 'pt'
    status = 'disabled'  # 2025/11 Switch to a custom website built with Next.js

    base_url = 'https://argoscomic.com'
    logo_url = base_url + '/wp-content/uploads/2024/06/cropped-argos-1-32x32.webp'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'

    details_synopsis_selector = '.manga-excerpt'
    chapters_selector = '.wp-manga-chapter'
