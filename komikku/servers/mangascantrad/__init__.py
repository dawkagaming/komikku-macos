# Copyright (C) 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

try:
    # This server requires JA3/TLS and HTTP2 fingerprints impersonation
    from curl_cffi import requests
except Exception:
    # Server will be disabled
    requests = None

from komikku.servers.multi.madara import Madara


class Mangascantrad(Madara):
    id = 'mangascantrad'
    name = 'Manga-Scantrad'
    lang = 'fr'
    is_nsfw = True
    status = 'enabled' if requests is not None else 'disabled'

    has_cf = True
    http_client = 'curl_cffi'

    date_format = None

    base_url = 'https://manga-scantrad.io'
    chapters_url = base_url + '/manga/{0}/ajax/chapters/'
    bypass_cf_url = base_url + '/manga/tales-of-demons-and-gods-scan-fr/'
