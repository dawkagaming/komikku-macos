import logging
import pytest
from pytest_steps import test_steps

from . import do_server_test
from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def nixofnothing_server():
    from komikku.servers.nixofnothing import Nixofnothing

    return Nixofnothing()


@do_server_test
@test_steps('get_most_populars', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_nixofnothing(nixofnothing_server):
    print('Get most popular')
    try:
        response = nixofnothing_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    print('Get manga data')
    try:
        response = nixofnothing_server.get_manga_data(response[0])
        chapter_slug = response['chapters'][0]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    print('Get chapter data')
    try:
        response = nixofnothing_server.get_manga_chapter_data(None, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    print('Get page image')
    try:
        response = nixofnothing_server.get_manga_chapter_page_image(None, None, chapter_slug, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield
