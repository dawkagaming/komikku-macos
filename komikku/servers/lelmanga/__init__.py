# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.manga_stream import MangaStream


class Lelmanga(MangaStream):
    id = 'lelmanga'
    name = 'Lelmanga'
    lang = 'fr'

    slug_position = -1

    base_url = 'https://www.lelmanga.com'
    manga_url = base_url + '/manga/{0}'

    authors_selector = '.tsinfo .imptdt:-soup-contains("Artiste") i, .tsinfo .imptdt:-soup-contains("Auteur") i'
    genres_selector = '.info-desc .mgen a'
    scanlators_selector = '.tsinfo .imptdt:-soup-contains("Sérialisation") i'
    status_selector = '.tsinfo .imptdt:-soup-contains("Status") i'
    synopsis_selector = '[itemprop="description"]'

    def get_manga_data(self, initial_data):
        data = MangaStream.get_manga_data(self, initial_data)
        if data is None:
            return None

        def convert(s):
            # Fix bad encoding
            try:
                s = s.replace('“', '"').replace('”', '"').replace("’", "'").replace("…", '...').encode('iso-8859-1').decode()
            except Exception:
                pass

            return s

        for key in ('authors', 'genres', 'scanlators', 'synopsis'):
            if isinstance(data[key], list):
                for index, value in enumerate(data[key]):
                    data[key][index] = convert(value)
            elif isinstance(data[key], str):
                data[key] = convert(data[key])

        return data
