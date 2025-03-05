# SPDX-FileCopyrightText: 2025 Seth Falco
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Seth Falco <seth@falco.fun>

from komikku.servers.multi.hiveworks import Hiveworks


class Wildlife(Hiveworks):
    id = 'wildlife'
    name = 'Wild Life'

    base_url = 'https://www.wildelifecomic.com'
    logo_url = base_url + '/favicon.ico'
    cover_url = base_url + '/image/patreon(2).jpg'
