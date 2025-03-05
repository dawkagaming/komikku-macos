# SPDX-FileCopyrightText: 2025 Seth Falco
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Seth Falco <seth@falco.fun>

from bs4 import BeautifulSoup

from komikku.servers.multi.hiveworks import Hiveworks


class Threepanelsoul(Hiveworks):
    id = 'threepanelsoul'
    name = 'Three Panel Soul'

    base_url = 'https://www.threepanelsoul.com'
    logo_url = base_url + '/favicon.ico'
    cover_url = None

    def get_metadata(self, soup: BeautifulSoup):
        return {
            'authors': [
                'Ian McConville',
                'Matthew Boyd',
            ],
            'synopsis': "It's a pretty rigid format but we keep the content loose, you know?",
        }
