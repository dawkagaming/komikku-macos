from functools import wraps

import pytest


def do_server_test(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        server = list(kwargs.values())[0]

        if server.status == 'disabled':
            pytest.skip('Server is disabled')

        if server.has_cf:
            pytest.skip('Server uses Cloudflare challenge')

        if server.has_captcha:
            pytest.skip('Server uses a CAPTCHA')

        return func(*args, **kwargs)

    return wrapper
