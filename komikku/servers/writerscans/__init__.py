# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup

from komikku.servers.multi.keyoapp import Keyoapp
from komikku.utils import get_buffer_mime_type


class Writerscans(Keyoapp):
    id = 'writerscans'
    name = 'Writer Scans'
    lang = 'en'

    base_url = 'https://writerscans.com'
    logo_url = 'https://wsrv.nl/?url=cdn.meowing.org/uploads/9fo4CQEukhQ&w=20'

    def get_most_populars(self):
        """
        Returns most popular manga
        """
        r = self.session_get(self.most_populars_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select('div.grid div:-soup-contains("Trending") button > a'):
            cover = a_element.div.div.get('style').replace('background-image:url', '')[1:-1]

            results.append(dict(
                slug=a_element.get('href').split('/')[-2],
                name=a_element.get('title'),
                cover=cover,
            ))

        return results
