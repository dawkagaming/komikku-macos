# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.fuzzydoodle import FuzzyDoodle


class Fleksyscans(FuzzyDoodle):
    id = 'fleksyscans'
    name = 'FleksyScans'
    lang = 'en'
    is_nsfw_only = True
    status = 'disabled'  # Dead 06/2024 DMCA

    base_url = 'https://flexscans.com'
    search_url = base_url + '/manga'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'

    # Selectors
    search_results_selector = '#card-real'
    search_link_selector = 'a'
    search_cover_img_selector = 'a > figure > img'

    most_popular_results_selector = '#popular-cards #card-real'  # does not currently exist 04/2024
    most_popular_link_selector = 'a'
    most_popular_cover_img_selector = 'a > figure > img'

    latest_updates_results_selector = '#latest > section > div > div'
    latest_updates_link_selector = '#card-real a'
    latest_updates_cover_img_selector = '#card-real a > figure > img'
    latest_updates_last_chapter_selector = 'div:last-child > a > div > b'

    details_name_selector = 'h1'
    details_cover_selector = 'main > section > div > div > div.relative > img'
    details_status_selector = 'main > section > div > div > div > div > p:-soup-contains("Status") > a > span'
    details_author_selector = 'main > section > div > div > div > div > p:-soup-contains("Author") > span:last-child'
    details_artist_selector = 'main > section > div > div > div > div > p:-soup-contains("Artist") > span:last-child'
    details_type_selector = 'main > section > div > div > div > div > p:-soup-contains("Type") > a > span'
    details_genres_selector = 'main > section > div > div:nth-child(2) > div > div:last-child > a'
    details_synopsis_selector = 'main > section > div > div:nth-child(2) > div:nth-child(2) > div > p'

    chapters_selector = '#chapters-list > a'
    chapters_title_selector = '#item-title'
    chapters_date_selector = 'div > span:last-child'

    chapter_pages_selector = '#chapter-container img'
