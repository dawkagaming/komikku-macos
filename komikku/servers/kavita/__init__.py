# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# Homepage: https://www.kavitareader.com/

import datetime
from functools import cached_property
from gettext import gettext as _
import logging

from komikku.servers import Server
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import do_login
from komikku.utils import get_buffer_mime_type
from komikku.utils import is_number

logger = logging.getLogger(__name__)

STATUSES = (
    'ongoing',
    'hiatus',
    'complete',
    'suspended',
    'complete',
)


class Kavita(Server):
    id = 'kavita'
    name = 'Kavita'
    description = _('Self-hosted digital library')
    lang = ''
    has_login = True
    sync = True

    base_url = None  # Customizable via the settings
    logo_url = 'https://www.kavitareader.com/assets/icons/favicon-32x32.png'

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Komikku Kavita',
    }

    def __init__(self, username=None, password=None, address=None):
        if address:
            self.base_url = address

        if username and password:
            self.do_login(username, password)

    @property
    def api_base_url(self):
        return self.base_url + '/api'

    @property
    def api_chapter_url(self):
        return self.api_base_url + '/Chapter'

    @property
    def api_chapter_read_progress(self):
        return self.api_base_url + '/Reader/progress'

    @property
    def api_chapters_url(self):
        return self.api_base_url + '/Series/series-detail'

    @property
    def api_cover_url(self):
        return self.api_base_url + f'/image/series-cover?seriesId={{{0}}}&apiKey={self.api_key}'

    @property
    def api_image_url(self):
        return self.api_base_url + '/Reader/image'

    @cached_property
    def api_key(self):
        return self.session.cookies.get('apiKey')

    @property
    def api_login_url(self):
        return self.api_base_url + '/Account/login'

    @property
    def api_manga_url(self):
        return self.api_base_url + '/Series/{0}'

    @property
    def api_manga_metadata_url(self):
        return self.api_base_url + '/Series/metadata'

    @property
    def api_search_url(self):
        return self.api_base_url + '/Search/search'

    @property
    def manga_url(self):
        return self.base_url + '/library/{0}/series/{1}'

    @do_login
    def get_manga_data(self, initial_data):
        """
        Returns serie data using API

        Initial data should contain at least serie's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        library_id, series_id = initial_data['slug'].split(':')

        r = self.session_get(
            self.api_manga_url.format(series_id),
            params={
                'seriesId': series_id,
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()

        data = initial_data.copy()
        data.update(dict(
            name=resp_data['name'],
            authors=[],
            scanlators=[],  # not available
            genres=[],
            status=None,
            synopsis=None,
            last_read=None,
            chapters=[],
            server_id=self.id,
            cover=self.api_cover_url.format(series_id),
        ))

        if latest_read_date := resp_data['latestReadDate']:
            data['last_read'] = datetime.datetime.strptime(latest_read_date[:-1], '%Y-%m-%dT%H:%M:%S.%f')

        r = self.session_get(
            self.api_manga_metadata_url,
            params={
                'seriesId': series_id,
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()

        data['status'] = STATUSES[resp_data['publicationStatus']]

        for key in ('genres', 'tags'):
            for item in resp_data[key]:
                if genre := item.get('name'):
                    data['genres'].append(genre)
                elif genre := item.get('title'):
                    data['genres'].append(genre)

        for key in ('writers',):
            for item in resp_data[key]:
                data['authors'].append(item['name'])

        data['synopsis'] = resp_data['summary']

        # Chapters
        r = self.session_get(
            self.api_chapters_url,
            params={
                'seriesId': series_id,
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()

        if resp_data['volumes']:
            for volume in resp_data['volumes']:
                for chapter in volume['chapters']:
                    title = f'{volume["name"]} - {chapter["title"]}'
                    if chapter['titleName']:
                        title = f'{title} {chapter["titleName"]}'

                    if modified_date := chapter.get('lastModifiedUtc'):
                        date = modified_date
                    else:
                        date = chapter['createdUtc']

                    if last_reading_progress := chapter.get('lastReadingProgress'):
                        if last_reading_progress.startswith('0001-01-01'):
                            last_read = None
                        else:
                            last_read = datetime.datetime.strptime(last_reading_progress[:-1], '%Y-%m-%dT%H:%M:%S.%f')
                    else:
                        last_read = None

                    chapter_data = dict(
                        slug=f'{volume["id"]}:{chapter["id"]}',  # noqa: E231
                        title=title,
                        num=chapter['number'] if is_number(chapter['number']) else None,
                        date=convert_date_string(date.split('T')[0], format='%Y-%m-%d'),
                        last_read=last_read,
                        last_page_read_index=chapter['pagesRead'] - 1,
                    )
                data['chapters'].append(chapter_data)

        elif resp_data['chapters']:
            # Chapters only, no volumes
            for chapter in resp_data['chapters']:
                if modified_date := chapter.get('lastModifiedUtc'):
                    date = modified_date
                else:
                    date = chapter['createdUtc']

                if last_reading_progress := chapter.get('lastReadingProgress'):
                    if last_reading_progress.startswith('0001-01-01'):
                        last_read = None
                    else:
                        last_read = datetime.datetime.strptime(last_reading_progress[:-1], '%Y-%m-%dT%H:%M:%S.%f')
                else:
                    last_read = None

                chapter_data = dict(
                    slug=f':{chapter["id"]}',  # noqa: E231
                    title=chapter['title'],
                    num=chapter['number'] if is_number(chapter['number']) else None,
                    date=convert_date_string(date.split('T')[0], format='%Y-%m-%d'),
                    last_read=last_read,
                    last_page_read_index=chapter['pagesRead'] - 1,
                )

                data['chapters'].append(chapter_data)

        return data

    @do_login
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns serie chapter data

        Currently, only pages are expected.
        """
        volume_id, chapter_id = chapter_slug.split(':')

        r = self.session_get(
            self.api_chapter_url,
            params={
                'chapterId': chapter_id,
            }
        )
        if r.status_code != 200:
            return None

        data = dict(
            pages=[],
        )
        for index in range(1, r.json()['files'][0]['pages'] + 1):
            data['pages'].append(dict(
                slug=str(index),
                image=None,
            ))

        return data

    @do_login
    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        volume_id, chapter_id = chapter_slug.split(':')

        r = self.session_get(
            self.api_image_url,
            params={
                'chapterId': chapter_id,
                'apiKey': self.api_key,
                'page': page['slug'],
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name='{0:04d}.{1}'.format(int(page['slug']), mime_type.split('/')[-1]),
        )

    @do_login
    def get_manga_url(self, slug, url):
        """
        Returns serie absolute URL
        """
        library_id, series_id = slug.split(':')

        return self.manga_url.format(library_id, series_id)

    def login(self, username, password):
        try:
            r = self.session.post(
                self.api_login_url,
                json={
                    'username': username,
                    'password': password,
                }
            )
            if r.status_code != 200:
                return False
        except Exception as error:
            logger.warning(error)
            return False

        resp_data = r.json()

        self.token = resp_data['token']
        self.session.cookies.set('apiKey', resp_data['apiKey'], domain=self.base_url)
        self.session.headers.update({'Authorization': f'Bearer {self.token}'})

        self.save_session()

        return True

    @do_login
    def search(self, term):
        r = self.session_get(
            self.api_search_url,
            params={
                'queryString': term,
                'includeChapterAndFiles': 'false',
            }
        )
        if r.status_code != 200:
            return None

        results = []
        for item in r.json()['series']:
            if item['format'] in (3, 4):
                # 0: ???
                # 1: Image
                # 2: ???
                # 3: HTML
                # 4: PDF
                continue

            results.append(dict(
                name=item['name'],
                slug=f'{item["libraryId"]}:{item["seriesId"]}',  # noqa: E231
                cover=self.api_cover_url.format(item['seriesId']),
            ))

        return results

    @do_login
    def update_chapter_read_progress(self, data, manga_slug, manga_name, chapter_slug, chapter_url):
        library_id, series_id = manga_slug.split(':')
        volume_id, chapter_id = chapter_slug.split(':')

        r = self.session_post(
            self.api_chapter_read_progress,
            json={
                'volumeId': volume_id,
                'chapterId': chapter_id,
                'pageNum': data['page'],
                'seriesId': series_id,
                'libraryId': library_id,
                # 'bookScrollId': 'string',
                'lastModifiedUtc': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            }
        )

        return r.status_code == 200
