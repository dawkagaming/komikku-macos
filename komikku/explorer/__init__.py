# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.explorer.search import ExplorerSearchPage
from komikku.explorer.servers import ExplorerServersPage


class Explorer:
    def __init__(self, window):
        self.window = window

        self.servers_page = ExplorerServersPage(self)
        self.window.navigationview.add(self.servers_page)
        self.search_page = ExplorerSearchPage(self)
        self.window.navigationview.add(self.search_page)

    def reinstantiate_servers(self):
        """Used when servers modules origin change: servers variables need to be re-instantiated"""

        self.servers_page.populate()
        self.search_page.reinstantiate_server(self.servers_page.servers)

    def show(self, servers=None):
        self.servers_page.show(servers)
