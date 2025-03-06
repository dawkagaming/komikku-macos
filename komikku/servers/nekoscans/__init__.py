# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.zeistmanga import ZeistManga


class Nekoscans(ZeistManga):
    id = 'nekoscans'
    name = 'Neko Scans'
    lang = 'es'
    is_nsfw = True

    base_url = 'https://nekoscanlation.blogspot.com'
    logo_url = 'https://blogger.googleusercontent.com/img/a/AVvXsEinOxcHo69oeHQGKoVyALGVhPv3kbA05NehCwMaLz6oCUf31akeRV818156JeO2yK5tIygqPHnobdi5Ss8tsiuopYZwSs9MmpbsTqvx8oFZNu1acu2QTAapG3fqiZ1KsOXoNNXUf2DnMworooS4mhduU0g-craRkk6bPsB0nJ1a5y8X1sSeGOlmHGRc71o=s116'

    most_popular_selector = 'div.PopularPosts .item-thumbnail a'
    details_name_selector = 'h1[itemprop="name"]'
    details_cover_selector = 'img.thumb'
    details_authors_selector = '#extra-info dl:-soup-contains("Autor") dd, #extra-info dl:-soup-contains("Artista") dd'
    details_type_selector = 'dl:-soup-contains("Type") dd a'
    details_genres_selector = 'dl:-soup-contains("Genre") dd a'
    details_status_selector = 'span[data-status]'
    details_synopsis_selector = '#synopsis'
    chapters_selector = '#clwd ul li'
    chapter_link_selector = 'a'
    chapter_title_selector = 'span.chapternum'
    chapter_date_selector = 'span.chapterdate'
    pages_selector = '#reader #readarea img'
