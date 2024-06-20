# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Argosscan(Madara):
    id = 'argosscan'
    name = 'Argos Comics'
    lang = 'pt'

    series_name = 'comics'

    base_url = 'https://argoscomic.com'
    chapters_url = base_url + '/comics/{0}/ajax/chapters/'

    details_synopsis_selector = '.manga-excerpt'
    chapters_selector = '.wp-manga-chapter.free-chap'
