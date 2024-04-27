# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import datetime
from functools import cache
from functools import wraps
import importlib
import inspect
from io import BytesIO
import itertools
import json
import logging
import math
from operator import itemgetter
import os
from pkgutil import iter_modules
import re
import struct
import sys
import time

from bs4 import NavigableString
from curl_cffi import requests
import dateparser
import emoji
import magic
from PIL import Image

from komikku.servers.loader import server_finder

logger = logging.getLogger(__name__)


def convert_date_string(date_string, format=None, languages=None):
    """
    Convert a date string into a date object

    :param date_string: A string representing date in a recognizably valid format
    :type date_string: str

    :param format: A format string using directives as given `here <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior>`_
    :type format: str

    :param languages: A list of language codes, e.g. ['en', 'es', 'zh-Hant']
    :type languages: list

    :return: A date object representing parsed date string if successful, `None` otherwise
    :rtype: datetime.date
    """
    if format is not None:
        try:
            d = datetime.datetime.strptime(date_string, format)
        except Exception:
            d = dateparser.parse(date_string, languages=languages)
    else:
        d = dateparser.parse(date_string, languages=languages)

    return d.date() if d else None


def convert_image(im, format='JPEG', ret_type='image'):
    """
    Convert an image to a specific format

    :param im: A `PIL.Image.Image` or `bytes` object
    :type im: PIL.Image.Image, bytes

    :param format: Convertion formats documentation is available `here <https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html>`_
    :type format: str

    :param ret_type: image or bytes
    :type ret_type: str

    :return: An new image object in requested format
    :rtype: PIL.Image.Image, bytes
    """
    if not isinstance(im, Image.Image):
        im = Image.open(BytesIO(im))

    io_buffer = BytesIO()
    with im.convert('RGB') as im_rgb:
        im_rgb.save(io_buffer, format)

    im.close()

    if ret_type == 'bytes':
        return io_buffer.getvalue()

    io_buffer.seek(0)

    return Image.open(io_buffer)


# https://github.com/italomaia/mangarock.py/blob/master/mangarock/mri_to_webp.py
def convert_mri_data_to_webp_buffer(data):
    size_list = [0] * 4
    size = len(data)
    header_size = size + 7

    # little endian byte representation
    # zeros to the right don't change the value
    for i, byte in enumerate(struct.pack('<I', header_size)):
        size_list[i] = byte

    buffer = [
        82,  # R
        73,  # I
        70,  # F
        70,  # F
        size_list[0],
        size_list[1],
        size_list[2],
        size_list[3],
        87,  # W
        69,  # E
        66,  # B
        80,  # P
        86,  # V
        80,  # P
        56,  # 8
    ]

    for bit in data:
        buffer.append(101 ^ bit)

    return bytes(buffer)


def do_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        server = args[0]
        if not server.logged_in:
            server.do_login()

        return func(*args, **kwargs)

    return wrapper


def get_allowed_servers_list(settings):
    servers_settings = settings.servers_settings
    servers_languages = settings.servers_languages

    servers = []
    for server_data in get_servers_list():
        if servers_languages and server_data['lang'] and server_data['lang'] not in servers_languages:
            continue

        server_settings = servers_settings.get(get_server_main_id_by_id(server_data['id']))
        if server_settings is not None:
            if (not server_settings['enabled']
                    or (len(servers_languages) > 1 and server_settings['langs'].get(server_data['lang']) is False)):
                # Server is disabled or several languages are selected and server language is disabled
                continue

        if settings.nsfw_content is False and server_data['is_nsfw']:
            continue
        if settings.nsfw_only_content is False and server_data['is_nsfw_only']:
            continue

        servers.append(server_data)

    return servers


def get_buffer_mime_type(buffer):
    """
    Returns the MIME type of a buffer

    :param buffer: A binary string
    :type buffer: bytes

    :return: The detected MIME type, empty string otherwise
    :rtype: str
    """
    try:
        if hasattr(magic, 'detect_from_content'):
            # Using file-magic module: https://github.com/file/file
            return magic.detect_from_content(buffer[:128]).mime_type  # noqa: TC300

        # Using python-magic module: https://github.com/ahupp/python-magic
        return magic.from_buffer(buffer[:128], mime=True)  # noqa: TC300
    except Exception:
        return ''


def get_file_mime_type(path):
    """
    Returns the MIME type of a file

    :param path: A file path
    :type path: str

    :return: The detected MIME type, empty string otherwise
    :rtype: str
    """
    try:
        if hasattr(magic, 'detect_from_filename'):
            # Using file-magic module: https://github.com/file/file
            return magic.detect_from_filename(path).mime_type  # noqa: TC300

        # Using python-magic module: https://github.com/ahupp/python-magic
        return magic.from_file(path, mime=True)  # noqa: TC300
    except Exception:
        return ''


def get_response_elapsed(r):
    """
    Returns the response time (in seconds) of a request
    regardless of the request type (requests, curl_cffi)

    :param r: A response
    :type r: requests.models.Response or curl_cffi.requests.models.Response

    :return: How many seconds the request cost
    :rtype: float
    """
    elapsed = r.elapsed
    if isinstance(elapsed, datetime.timedelta):
        # requests
        return elapsed.total_seconds()

    # curl_cffi
    return elapsed


def get_server_class_name_by_id(id):
    """
    Returns a server class name from its ID

    `id` must respect the following format: `name[_lang][_whatever][:module_name]`

    + `name` is the name of the server.
    + `lang` is the language of the server (optional).
        Only useful when server belongs to a multi-languages server.
    + `whatever` is any string (optional).
        Only useful when a server must be backed up because it's dead.
        Beware, if `whatever` is defined, `lang` must be present even if it's empty.
        Example of value: old, bak, dead,...
    + `module_name` is the name of the module in which the server is defined (optional).
        Only useful if `module_name` is different from `name`.

    Parameters
    ----------
    :param id: A server ID
    :type id: str

    :return: The server class name corresponding to ID
    :rtype: str
    """
    return id.split(':')[0].capitalize()


def get_server_dir_name_by_id(id):
    name = id.split(':')[0]
    # Remove _whatever
    name = '_'.join(filter(None, name.split('_')[:2]))

    return name


def get_server_main_id_by_id(id):
    return id.split(':')[0].split('_')[0]


def get_server_module_name_by_id(id):
    return id.split(':')[-1].split('_')[0]


@cache
def get_servers_list(include_disabled=False, order_by=('lang', 'name')):
    def iter_namespace(ns_pkg):
        # Specifying the second argument (prefix) to iter_modules makes the
        # returned name an absolute name instead of a relative one. This allows
        # import_module to work without having to do additional modification to
        # the name.
        return iter_modules(ns_pkg.__path__, ns_pkg.__name__ + '.')

    modules = []
    if server_finder in sys.meta_path:
        # Load servers from external folders defined in KOMIKKU_SERVERS_PATH environment variable
        for servers_path in server_finder.paths:
            if not os.path.exists(servers_path):
                continue

            count = 0
            for path, _dirs, _files in os.walk(servers_path):
                relpath = path[len(servers_path):]
                if not relpath:
                    continue

                relname = relpath.replace(os.path.sep, '.')
                if relname == '.multi':
                    continue

                modules.append(importlib.import_module(relname, package='komikku.servers'))
                count += 1

            logger.info('Load {0} servers from external folder: {1}'.format(count, servers_path))
    else:
        # fallback to local exploration
        import komikku.servers

        for _finder, name, _ispkg in iter_namespace(komikku.servers):
            modules.append(importlib.import_module(name))

    servers = []
    for module in modules:
        for _name, obj in dict(inspect.getmembers(module)).items():
            if not hasattr(obj, 'id') or not hasattr(obj, 'name') or not hasattr(obj, 'lang'):
                continue
            if NotImplemented in (obj.id, obj.name, obj.lang):
                continue

            if not include_disabled and obj.status == 'disabled':
                continue

            if inspect.isclass(obj):
                logo_path = os.path.join(os.path.dirname(os.path.abspath(module.__file__)), get_server_main_id_by_id(obj.id) + '.png')

                servers.append(dict(
                    id=obj.id,
                    name=obj.name,
                    lang=obj.lang,
                    has_login=obj.has_login,
                    is_nsfw=obj.is_nsfw,
                    is_nsfw_only=obj.is_nsfw_only,
                    class_name=get_server_class_name_by_id(obj.id),
                    logo_path=logo_path if os.path.exists(logo_path) else None,
                    module=module,
                ))

    return sorted(servers, key=itemgetter(*order_by))


def get_soup_element_inner_text(tag, text=None, recursive=True):
    """
    Returns inner text of a tag

    :param tag: A Tag
    :type tag: bs4.element.Tag

    :param text: A optional list of text strings to prepend
    :type text: list of str

    :param recursive: Recursively walk in children or not
    :type recursive: bool

    :return: The inner text of tag
    :rtype: str
    """
    if text is None:
        text = []

    for el in tag:
        if isinstance(el, NavigableString):
            text.append(el.strip())
        elif recursive:
            get_soup_element_inner_text(el, text)

    return ' '.join(text).strip()


def sojson4_decode(s):
    """
    Decodes a Sojson v4 string

    :param s: A string
    :type s: str

    :return: The decoded string
    :rtype: str
    """
    ss = re.split(r'[a-zA-Z]{1,}', s[240:-58])
    sss = ''
    for c in ss:
        sss += chr(int(c))

    return sss


def remove_emoji_from_string(text):
    """
    Removes Emojis from text (use emoji package)

    :param text: A text string
    :type text: str

    :return: The text string freed from Emojis
    :rtype: str
    """
    return emoji.replace_emoji(text, replace='').strip()


def search_duckduckgo(site, term, nb_pages=1):
    """
    Searches DuckDuckGo lite

    :param site: the site URL
    :type site: str

    :param term: the term to search for
    :type term: str

    :param nb_pages: the number of results pages to parse
    :type nb_pages: int

    :return: A list of dictionaries (name, url)
    :rtype: list of dict
    """

    from komikku.servers import USER_AGENT

    # https://github.com/deedy5/duckduckgo_search/blob/main/duckduckgo_search/duckduckgo_search_async.py
    session = requests.Session(impersonate='chrome')
    session.headers.update({'User-Agent': USER_AGENT, 'Referer': 'https://duckduckgo.com/'})

    def extract_vqd(html_bytes, keywords):
        """Extract vqd param from HTML bytes"""
        for c1, c1_len, c2 in (
            (b'vqd="', 5, b'"'),
            (b"vqd=", 4, b"&"),
            (b"vqd='", 5, b"'"),
        ):
            try:
                start = html_bytes.index(c1) + c1_len
                end = html_bytes.index(c2, start)
            except ValueError:
                return None
            else:
                return html_bytes[start:end].decode()

    def extract_json(html_bytes, keywords):
        """Extract JSON from HTML bytes"""
        try:
            start = html_bytes.index(b"DDG.pageLayout.load('d',") + 24
            end = html_bytes.index(b");DDG.duckbar.load(", start)
            data = html_bytes[start:end]
            result = json.loads(data)
        except Exception:
            return None
        else:
            return result

    def get_page(num, q, vqd):
        url = 'https://links.duckduckgo.com/d.js'
        s = 23 + 50 * (num - 1) if num > 0 else 0

        r = session.get(
            url,
            params={
                'q': q,
                'kl': 'wt-wt',
                "l": 'wt-wt',
                'vqd': vqd,
                'bing_market': 'wt-wt',
                'a': 'ftsa',  # something
                's': s,
            }
        )
        if result := extract_json(r.content, q):
            return result

        logger.exception('DuckDuckGo search: failed to extract JSON')
        return []

    q = f'site:{site} {term}'
    r = session.get('https://duckduckgo.com', params={'q': q})

    vqd = extract_vqd(r.content, q)
    if vqd is None:
        logger.exception('DuckDuckGo search: failed to extract vqd parameter')
        return []

    data = []
    for num in range(nb_pages):
        data += get_page(num, q, vqd)
        time.sleep(1)

    results = []
    for item in data:
        url = item.get('u')
        if not url or url == f'http://www.google.com/search?q={q}':
            continue

        results.append(dict(
            name=item.get('t'),
            url=url,
        ))

    return results


# https://github.com/Harkame/JapScanDownloader
def unscramble_image(image):
    """
    Unscrambles an image

    :param image: An image object
    :type image: PIL.Image.Image, bytes

    :return: A new unscrambled image
    :rtype: PIL.Image.Image
    """
    if not isinstance(image, Image.Image):
        image = Image.open(BytesIO(image))

    temp = Image.new('RGB', image.size)
    output_image = Image.new('RGB', image.size)

    for x in range(0, image.width, 200):
        col1 = image.crop((x, 0, x + 100, image.height))

        if x + 200 <= image.width:
            col2 = image.crop((x + 100, 0, x + 200, image.height))
            temp.paste(col1, (x + 100, 0))
            temp.paste(col2, (x, 0))
        else:
            col2 = image.crop((x + 100, 0, image.width, image.height))
            temp.paste(col1, (x, 0))
            temp.paste(col2, (x + 100, 0))

    for y in range(0, temp.height, 200):
        row1 = temp.crop((0, y, temp.width, y + 100))

        if y + 200 <= temp.height:
            row2 = temp.crop((0, y + 100, temp.width, y + 200))
            output_image.paste(row1, (0, y + 100))
            output_image.paste(row2, (0, y))
        else:
            row2 = temp.crop((0, y + 100, temp.width, temp.height))
            output_image.paste(row1, (0, y))
            output_image.paste(row2, (0, y + 100))

    return output_image


class RC4:
    """ RC4 (Rivest Cipher 4) stream cipher"""

    def __init__(self, key):
        self.key = key.encode()
        self.keystream = self.PRGA(self.KSA())

        # RC4-drop[256]
        for _i in range(256):
            next(self.keystream)

    def KSA(self):
        # Initialize S as a list of integers from 0 to 255
        S = list(range(256))
        j = 0

        for i in range(256):
            j = (j + S[i] + self.key[i % len(self.key)]) % 256
            # Swap values
            S[i], S[j] = S[j], S[i]

        return S

    def PRGA(self, S):
        i = j = 0

        while True:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            # Swap values
            S[i], S[j] = S[j], S[i]
            K = S[(S[i] + S[j]) % 256]
            yield K


class RC4SeedRandom:
    def __init__(self, key):
        self.key = key
        self.pos = 256

    def get_next(self):
        if self.pos == 256:
            self.keystream = RC4(self.key).keystream
            self.pos = 0
        self.pos += 1

        return next(self.keystream)


def unscramble_image_rc4(image, key, piece_size):
    """
    Unscrambles an image shuffled with RC4 stream cipher

    :param image: An image object
    :type image: PIL.Image.Image, bytes

    :param key: The key
    :type key: str

    :param piece_size: The pieces size
    :type piece_size: int

    :return: A new unscrambled image
    :rtype: PIL.Image.Image
    """
    if not isinstance(image, Image.Image):
        image = Image.open(BytesIO(image))

    output_image = Image.new('RGB', image.size)

    pieces = []
    for j in range(math.ceil(image.height / piece_size)):
        for i in range(math.ceil(image.width / piece_size)):
            pieces.append(dict(
                x=piece_size * i,
                y=piece_size * j,
                w=min(piece_size, image.width - piece_size * i),
                h=min(piece_size, image.height - piece_size * j)
            ))

    groups = {}
    for k, v in itertools.groupby(pieces, key=lambda x: x['w'] << 16 | x['h']):
        if k not in groups:
            groups[k] = []
        groups[k] += list(v)

    for _w, group in groups.items():
        size = len(group)

        permutation = []
        indexes = list(range(size))
        random = RC4SeedRandom(key)
        for i in range(size):
            num = random.get_next()
            exp = 8
            while num < (1 << 52):
                num = num << 8 | random.get_next()
                exp += 8
            while num >= (1 << 53):
                num = num >> 1
                exp -= 1

            permutation.append(indexes.pop(int(num * (2 ** -exp) * len(indexes))))

        for i, original in enumerate(permutation):
            src = group[i]
            dst = group[original]

            src_piece = image.crop((src['x'], src['y'], src['x'] + src['w'], src['y'] + src['h']))
            output_image.paste(src_piece, (dst['x'], dst['y']))

    return output_image
