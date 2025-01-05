# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara2


class Argosscan(Madara2):
    id = 'argosscan'
    name = 'Argos Comics'
    lang = 'pt'

    base_url = 'https://argoscomic.com'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'

    details_synopsis_selector = '.manga-excerpt'
    chapters_selector = '.wp-manga-chapter'

    ignore_ssl_errors = True
