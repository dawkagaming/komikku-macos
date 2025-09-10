# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara2

# 2025/01 fusion of Sinensis and Cerise => SCtoon (Peachscan)
# 2025/09 SCtoon => Lovers Toon (Madara)


class Sinensistoon(Madara2):
    id = 'sinensistoon'
    name = 'Lovers Toon (SCtoon)'
    lang = 'pt_BR'
    status = 'disabled'  # chapters are only accessible by visiting another site (with ads)

    date_format = None

    base_url = 'https://loverstoon.com'
    logo_url = base_url + '/wp-content/uploads/2025/09/cropped-faviliocon-32x32.png'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'
