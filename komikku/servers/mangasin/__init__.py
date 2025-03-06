# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import base64
import json
import re

from bs4 import BeautifulSoup
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import modes

from komikku.servers.multi.my_manga_reader_cms import MyMangaReaderCMS
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type


def md5(text):
    """
    Returns the MD5 digest of ``text`` as bytes

    ``text`` is a ``bytes`` instance
    """
    digest = hashes.Hash(hashes.MD5())
    digest.update(text)

    return digest.finalize()


def generate_key(passphrase, salt):
    """
    Generates the key from ``passphrase`` and ``salt`` as bytes

    ``passphrase`` is a ``bytes`` instance
    ``salt`` is a ``bytes`` instance
    """
    passphrase += salt
    md5arr = [0] * 3
    md5arr[0] = md5(passphrase)

    key = md5arr[0]
    for i in range(1, 3):
        md5arr[i] = md5(md5arr[i - 1] + passphrase)
        key += md5arr[i]

    return key[:32]


class Mangasin(MyMangaReaderCMS):
    id = 'mangasin'
    name = 'M440.in (Mangas.in)'
    lang = 'es'
    is_nsfw = True

    search_query_param = 'q'

    base_url = 'https://m440.in'
    logo_url = base_url + '/favicon.ico'
    search_url = base_url + '/search'
    most_populars_url = base_url + '/filterList?page=1&cat=&alpha=&sortBy=views&asc=false&author=&tag=&artist='
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'
    image_url = None  # Images URLs can't be computed with manga/chapter/image slugs
    cover_url = base_url + '/uploads/manga/{0}/cover/cover_250x350.jpg'

    def get_manga_chapters_data(self, soup):
        chapters_data = None
        chapters_re = r'{(?=.*\\"ct\\")(?=.*\\"iv\\")(?=.*\\"s\\").*?}'

        for script_element in soup.select('script'):
            script = script_element.string
            if script is None or not re.findall(chapters_re, script):
                continue

            line = re.findall(chapters_re, script)[0]
            cdata = json.loads(json.loads(f'"{line}"'))

            # Decrypt
            passphrase = b'X^Ib1O*HLVh%3W2t'  # in js/ads2.js, must be deobfuscated
            dct = base64.b64decode(cdata['ct'])
            iv = bytes.fromhex(cdata['iv'])
            salt = bytes.fromhex(cdata['s'])
            key = generate_key(passphrase, salt)

            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            chapters_data = decryptor.update(dct) + decryptor.finalize()

            unpadder = padding.PKCS7(128).unpadder()
            chapters_data = unpadder.update(chapters_data)
            chapters_data = chapters_data + unpadder.finalize()

            chapters_data = json.loads(json.loads(chapters_data.decode('utf-8')))
            break

        if chapters_data is None:
            return []

        data = []
        for chapter in reversed(chapters_data):
            data.append(dict(
                slug=chapter['slug'],
                title=f'Vol {chapter["volume"]} - #{chapter["number"]} {chapter["name"]}',
                num=chapter['number'],
                num_volume=chapter['volume'],
                date=convert_date_string(chapter['updated_at'].split()[0], format='%Y-%m-%d'),
            ))

        return data

    def get_latest_updates(self):
        """
        Returns list of latest updated manga
        """
        r = self.session_get(
            self.base_url,
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for a_element in soup.select('.mangalist .manga-item h3 a:nth-child(3)'):
            slug = a_element.get('href').split('/')[-1]
            results.append(dict(
                name=a_element.text.strip(),
                slug=slug,
                cover=self.cover_url.format(slug),
            ))

        return results
