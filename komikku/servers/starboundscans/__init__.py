# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara2


class Starboundscans(Madara2):
    id = 'starboundscans'
    name = 'Starbound Scans'
    lang = 'fr'
    status = 'disabled'

    base_url = 'https://starboundscans.com'
    logo_url = base_url + '/wp-content/uploads/2025/07/cropped-g_logo-1-32x32.png'
    chapter_url = base_url + '/manga/{0}/{1}/'

    details_authors_selector = '.info-item:-soup-contains("Auteur") a'
    details_scanlators_selector = '.info-item:-soup-contains("Team") a'
    details_genres_selector = '.info-item:-soup-contains("Genres") .genre-tag'
    details_status_selector = '.info-item:-soup-contains("Statut") .info-value'
    details_synopsis_selector = '.card-body .black-orion-article-content p'

    chapters_selector = '.chapters-list .chapter-content'
