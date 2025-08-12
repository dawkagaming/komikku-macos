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
def jensorensen_server():
    from komikku.servers.jensorensen import Jensorensen

    return Jensorensen()


@do_server_test
@test_steps('get_most_populars', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_jensorensen(jensorensen_server):
    # Get most popular
    print('Get most popular')
    try:
        response = jensorensen_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Get comic data
    print('Get comic data')
    try:
        response = jensorensen_server.get_manga_data(response[0])
        chapter_slug = response['chapters'][0]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print('Get chapter data')
    try:
        response = jensorensen_server.get_manga_chapter_data(None, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = jensorensen_server.get_manga_chapter_page_image(None, None, chapter_slug, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield
