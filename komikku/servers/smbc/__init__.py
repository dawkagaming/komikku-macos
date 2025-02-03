# Copyright (C) 2025-2025 Seth Falco
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Seth Falco <seth@falco.fun>

import json

from bs4 import BeautifulSoup

from komikku.servers.multi.hiveworks import Hiveworks


class Smbc(Hiveworks):
    id = 'smbc'
    name = 'SMBC'
    base_url = 'https://www.smbc-comics.com'
    cover_url = base_url + '/images/moblogo.png'

    def get_metadata(self, soup: BeautifulSoup):
        linked_data_str = soup.find('script', attrs={'type': 'application/ld+json'}).contents[0]
        linked_data = json.loads(linked_data_str)
        return {
            'authors': [linked_data['author'], ],
            'synopsis': soup.find_all('meta', {'name': 'description'})[-1].get('content'),
        }
