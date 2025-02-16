# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.fuzzydoodle import FuzzyDoodle


class Scyllacomics(FuzzyDoodle):
    id = 'scyllacomics'
    name = 'Scylla Comics'
    lang = 'en'
    is_nsfw = True

    base_url = 'https://scyllacomics.xyz'
    search_url = base_url + '/manga'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'

    # Selectors
    search_results_selector = '#card-real'
    search_link_selector = 'a'
    search_cover_img_selector = 'a > figure > img'

    most_popular_results_selector = '#popular-cards #card-real'
    most_popular_link_selector = 'a'
    most_popular_cover_img_selector = 'a > figure > img'

    latest_updates_results_selector = 'main section:last-child > div:nth-child(2) > div'
    latest_updates_link_selector = '#card-real a'
    latest_updates_cover_img_selector = '#card-real a > figure > img'
    latest_updates_last_chapter_selector = 'div:last-child > div > a > b'

    details_name_selector = 'main > section > div > div:nth-child(2) > div:nth-child(4) > h2'
    details_cover_selector = 'main > section > div > div > div.relative > img'
    details_status_selector = 'main > section > div > div > div.hidden > p:-soup-contains("Status") > a > span'
    details_author_selector = 'main > section > div > div > div.hidden > p:-soup-contains("Author") > span:last-child'
    details_artist_selector = 'main > section > div > div > div.hidden > p:-soup-contains("Artist") > span:last-child'
    details_type_selector = 'main > section > div > div > div.hidden > p:-soup-contains("Type") > a > span'
    details_genres_selector = 'main > section > div > div:nth-child(2) > div.flex.flex-wrap.gap-1 a'
    details_synopsis_selector = 'main > section > div > div:nth-child(2) > div:nth-child(4) > div p'

    chapters_selector = '#chapters-list > a'
    chapters_title_selector = 'div > div > span'
    chapters_date_selector = 'div > div:nth-child(2) > span'

    chapter_pages_selector = '#chapter-container img'
