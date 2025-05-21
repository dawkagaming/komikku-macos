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
def bluesolo_server():
    from komikku.servers.bluesolo import Bluesolo

    return Bluesolo()


@do_server_test
@test_steps('get_latest_updates', 'get_most_populars', 'search', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_bluesolo(bluesolo_server):
    # Get latest updates
    print('Get latest updates')
    try:
        response = bluesolo_server.get_latest_updates()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Get most populars
    print('Get most populars')
    try:
        response = bluesolo_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Search
    print('Search')
    try:
        # Use first result of get_most_populars
        response = bluesolo_server.search(response[0]['name'])
        slug = response[0]['slug']
    except Exception as e:
        slug = None
        log_error_traceback(e)

    assert slug is not None
    yield

    # Get manga data
    print('Get manga data')
    try:
        response = bluesolo_server.get_manga_data(dict(slug=slug))
        chapter_url = response['chapters'][0]['url']
    except Exception as e:
        chapter_url = None
        log_error_traceback(e)

    assert chapter_url is not None
    yield

    # Get chapter data
    print("Get chapter data")
    try:
        response = bluesolo_server.get_manga_chapter_data(slug, None, None, chapter_url)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = bluesolo_server.get_manga_chapter_page_image(None, None, None, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield
