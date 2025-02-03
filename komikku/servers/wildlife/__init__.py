# Copyright (C) 2025-2025 Seth Falco
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Seth Falco <seth@falco.fun>

from komikku.servers.multi.hiveworks import Hiveworks


class Wildlife(Hiveworks):
    id = 'wildlife'
    name = 'Wild Life'
    base_url = 'https://www.wildelifecomic.com'
    cover_url = base_url + '/images/logo.png'
