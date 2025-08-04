# SPDX-FileCopyrightText: 2019-2025 Contributors to Komikku
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import pytest
from pytest_steps import test_steps

from . import do_server_test
from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def server():
    from komikku.servers.coloredcouncil import Coloredcouncil

    return Coloredcouncil()


@do_server_test
@test_steps('get_latest_updates', 'get_most_populars', 'search', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_coloredcouncil(server):
    # Get latest updates
    print('Get latest updates')
    try:
        response = server.get_latest_updates('')
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Get most popular
    print('Get most popular')
    try:
        response = server.get_most_populars('')
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Search
    print('Search')
    try:
        # Use first result of get_most_populars
        response = server.search(response[0]['name'], '')
        slug = response[0]['slug']
        name = response[0]['name']
    except Exception as e:
        slug = None
        log_error_traceback(e)

    assert slug is not None
    yield

    # Get manga data
    print('Get manga data')
    try:
        response = server.get_manga_data(dict(slug=slug))
        chapter_slug = response['chapters'][0]['slug']
        chapter_url = response['chapters'][0]['url']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print('Get chapter data')
    try:
        response = server.get_manga_chapter_data(slug, None, chapter_slug, chapter_url)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = server.get_manga_chapter_page_image(slug, name, chapter_slug, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield
