# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

#
# API doc: https://api.mangadex.org
#

from gettext import gettext as _
from functools import lru_cache
import html
import logging
from uuid import UUID

import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.exceptions import NotFoundError
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type

logger = logging.getLogger('komikku.servers.mangadex')

SERVER_NAME = 'MangaDex'

CHAPTERS_PER_REQUEST = 100
SEARCH_RESULTS_LIMIT = 50


class Mangadex(Server):
    id = 'mangadex'
    name = SERVER_NAME
    lang = 'en'
    lang_code = 'en'
    is_nsfw = True
    long_strip_genres = ['Long Strip', ]

    base_url = 'https://mangadex.org'
    api_base_url = 'https://api.mangadex.org'
    api_manga_base = api_base_url + '/manga'
    api_manga_url = api_manga_base + '/{0}'
    api_chapter_base = api_base_url + '/chapter'
    api_chapter_url = api_chapter_base + '/{0}'
    api_author_base = api_base_url + '/author'
    api_cover_url = api_base_url + '/cover/{0}'
    api_scanlator_base = api_base_url + '/group'
    api_server_url = api_base_url + '/at-home/server/{0}'

    manga_url = base_url + '/title/{0}'
    page_image_url = '{0}/data/{1}/{2}'
    cover_url = 'https://uploads.mangadex.org/covers/{0}/{1}.256.jpg'

    filters = [
        {
            'key': 'ratings',
            'type': 'select',
            'name': _('Rating'),
            'description': _('Filter by content ratings'),
            'value_type': 'multiple',
            'options': [
                {'key': 'safe', 'name': _('Safe'), 'default': True},
                {'key': 'suggestive', 'name': _('Suggestive'), 'default': True},
                {'key': 'erotica', 'name': _('Erotica'), 'default': False},
                {'key': 'pornographic', 'name': _('Pornographic'), 'default': False},
            ]
        },
        {
            'key': 'statuses',
            'type': 'select',
            'name': _('Status'),
            'description': _('Filter by statuses'),
            'value_type': 'multiple',
            'options': [
                {'key': 'ongoing', 'name': _('Ongoing'), 'default': False},
                {'key': 'completed', 'name': _('Completed'), 'default': False},
                {'key': 'hiatus', 'name': _('Paused'), 'default': False},
                {'key': 'cancelled', 'name': _('Canceled'), 'default': False},
            ]
        },
        {
            'key': 'publication_demographics',
            'type': 'select',
            'name': _('Publication Demographic'),
            'description': _('Filter by publication demographics'),
            'value_type': 'multiple',
            'options': [
                {'key': 'shounen', 'name': _('Shounen'), 'default': False},
                {'key': 'shoujo', 'name': _('Shoujo'), 'default': False},
                {'key': 'josei', 'name': _('Josei'), 'default': False},
                {'key': 'seinen', 'name': _('Seinen'), 'default': False},
            ]
        },
        {
            'key': 'tags',
            'type': 'select',
            'name': _('Tags'),
            'description': _('Filter by formats'),
            'value_type': 'multiple',
            'options': [
                {'key': 'b11fda93-8f1d-4bef-b2ed-8803d3733170', 'name': _('4-Koma'), 'default': False},
                {'key': 'f4122d1c-3b44-44d0-9936-ff7502c39ad3', 'name': _('Adaptation'), 'default': False},
                {'key': '51d83883-4103-437c-b4b1-731cb73d786c', 'name': _('Anthology'), 'default': False},
                {'key': '0a39b5a1-b235-4886-a747-1d05d216532d', 'name': _('Award Winning'), 'default': False},
                {'key': 'b13b2a48-c720-44a9-9c77-39c9979373fb', 'name': _('Doujinshi'), 'default': False},
                {'key': '7b2ce280-79ef-4c09-9b58-12b7c23a9b78', 'name': _('Fan Colored'), 'default': False},
                {'key': 'f5ba408b-0e7a-484d-8d49-4e9125ac96de', 'name': _('Full Color'), 'default': False},
                {'key': '3e2b8dae-350e-4ab8-a8ce-016e844b9f0d', 'name': _('Long Strip'), 'default': False},
                {'key': '320831a8-4026-470b-94f6-8353740e6f04', 'name': _('Official Colored'), 'default': False},
                {'key': '0234a31e-a729-4e28-9d6a-3f87c4966b9e', 'name': _('Oneshot'), 'default': False},
                {'key': '891cf039-b895-47f0-9229-bef4c96eccd4', 'name': _('Self-Published'), 'default': False},
                {'key': 'e197df38-d0e7-43b5-9b09-2842d0c326dd', 'name': _('Web Comic'), 'default': False},
            ]
        },
        {
            'key': 'tags_mode',
            'type': 'select',
            'name': _('Tags Inclusion Mode'),
            'description': _('Include manga that match <b>all</b> tags (AND) or <b>any</b> tag (OR)'),
            'value_type': 'single',
            'default': 'AND',
            'options': [
                {'key': 'AND', 'name': _('AND')},
                {'key': 'OR', 'name': _('OR')},
            ],
        },
    ]

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    @staticmethod
    def get_group_name(group_id, groups_list):
        """Get group name from group id"""
        matching_group = [group for group in groups_list if group['id'] == group_id]

        return matching_group[0]['name']

    def __convert_old_slug(self, slug, type):
        # Removing this will break manga that were added before the change to the manga slug
        slug = slug.split('/')[0]
        try:
            return str(UUID(slug, version=4))
        except ValueError:
            r = self.session_post(self.api_base_url + '/legacy/mapping', json={
                'type': type,
                'ids': [int(slug)],
            })
            if r.status_code != 200:
                return None

            for result in r.json():
                if result['result'] == 'ok' and str(result['data']['attributes']['legacyId']) == slug:
                    return result['data']['attributes']['newId']

            return None

    def __get_manga_title(self, attributes):
        # Check if title is available in server language
        if self.lang_code in attributes['title']:
            return attributes['title'][self.lang_code]

        # Fallback to English title
        if 'en' in attributes['title']:
            return attributes['title']['en']

        # Search in alternative titles
        # NOTE: Some weird stuff can happen here. For ex., French translations that are in German!
        for alt_title in attributes['altTitles']:
            if self.lang_code in alt_title:
                return alt_title[self.lang_code]

            if 'en' in alt_title:
                return alt_title['en']

        # Last resort
        if len(attributes['title']) > 0:
            return list(attributes['title'].values())[0]

        return None

    @lru_cache(maxsize=1)
    def __get_chapter_json(self, chapter_slug):
        r = self.session_get(self.api_server_url.format(chapter_slug))
        if r.status_code != 200:
            return None

        return r.json()

    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        slug = self.__convert_old_slug(initial_data['slug'], type='manga')
        if slug is None:
            raise NotFoundError

        r = self.session_get(self.api_manga_url.format(slug), params={'includes[]': ['author', 'artist', 'cover_art']})
        if r.status_code != 200:
            return None

        resp_json = r.json()

        data = initial_data.copy()
        data.update(dict(
            slug=slug,
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            cover=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        attributes = resp_json['data']['attributes']

        _name = self.__get_manga_title(attributes)
        data['name'] = html.unescape(_name)
        assert data['name'] is not None

        for relationship in resp_json['data']['relationships']:
            if relationship['type'] == 'author':
                data['authors'].append(relationship['attributes']['name'])
            elif relationship['type'] == 'cover_art':
                data['cover'] = self.cover_url.format(slug, relationship['attributes']['fileName'])

        # NOTE: not suitable translations for genres
        data['genres'] = [tag['attributes']['name']['en'] for tag in attributes['tags']]

        if attributes['status'] == 'ongoing':
            data['status'] = 'ongoing'
        elif attributes['status'] == 'completed':
            data['status'] = 'complete'
        elif attributes['status'] == 'cancelled':
            data['status'] = 'suspended'
        elif attributes['status'] == 'hiatus':
            data['status'] = 'hiatus'

        if self.lang_code in attributes['description']:
            data['synopsis'] = html.unescape(attributes['description'][self.lang_code])
        elif 'en' in attributes['description']:
            # Fall back to english synopsis
            data['synopsis'] = html.unescape(attributes['description']['en'])
        else:
            logger.warning('{}: No synopsis', data['name'])

        data['chapters'] += self.resolve_chapters(data['slug'])

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data from API

        Currently, only pages are expected.
        """
        r = self.session_get(self.api_chapter_url.format(chapter_slug), params={'includes[]': ['scanlation_group']})
        if r.status_code == 404:
            raise NotFoundError
        if r.status_code != 200:
            return None

        data = r.json()['data']

        attributes = data['attributes']
        title = f'#{attributes["chapter"]}'
        if attributes['title']:
            title = f'{title} - {attributes["title"]}'

        scanlators = [rel['attributes']['name'] for rel in data['relationships'] if rel['type'] == 'scanlation_group']
        data = dict(
            slug=chapter_slug,
            title=title,
            pages=[dict(index=page, image=None) for page in range(0, attributes['pages'])],
            date=convert_date_string(attributes['publishAt'].split('T')[0], format='%Y-%m-%d'),
            scanlators=scanlators,
        )

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        chapter_json = self.__get_chapter_json(chapter_slug)
        if chapter_json is None:
            self.__get_chapter_json.cache_clear()
            return None

        server_url = chapter_json['baseUrl']
        chapter_hash = chapter_json['chapter']['hash']
        slug = None
        if 'data' in chapter_json['chapter']:
            slug = chapter_json['chapter']['data'][page['index']]
        else:
            slug = chapter_json['chapter']['dataSaver'][page['index']]

        r = self.session_get(self.page_image_url.format(server_url, chapter_hash, slug))
        if r.status_code != 200:
            self.__get_chapter_json.cache_clear()
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=slug,
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_latest_updates(self, ratings=None, statuses=None, publication_demographics=None, tags=None, tags_mode=None):
        params = {
            'limit': CHAPTERS_PER_REQUEST,
            'contentRating[]': ratings,
            'includes[]': ['manga'],
            'translatedLanguage[]': [self.lang_code],
            'order[readableAt]': 'desc',
        }

        r = self.session_get(self.api_chapter_base, params=params)
        if r.status_code != 200:
            return None

        manga_ids = set()
        for chapter in r.json()['data']:
            for relationship in chapter['relationships']:
                if relationship['type'] == 'manga':
                    manga_ids.add(relationship['id'])

        params = {
            'ids[]': list(manga_ids),
            'limit': SEARCH_RESULTS_LIMIT,
            'contentRating[]': ratings,
            'status[]': statuses,
            'includes[]': ['cover_art'],
            'includedTags[]': tags,
            'includedTagsMode': tags_mode,
            'publicationDemographic[]': publication_demographics,
            'availableTranslatedLanguage[]': [self.lang_code],
            'order[latestUploadedChapter]': 'desc',
        }

        r = self.session_get(self.api_manga_base, params=params)
        if r.status_code != 200:
            return None

        results = []
        for manga in r.json()['data']:
            name = self.__get_manga_title(manga['attributes'])

            cover = None
            for relationship in manga['relationships']:
                if relationship['type'] == 'cover_art':
                    cover = self.cover_url.format(manga['id'], relationship['attributes']['fileName'])
                    break

            if name:
                results.append({
                    'slug': manga['id'],
                    'name': name,
                    'cover': cover,
                })
            else:
                logger.warning('Ignoring result {}, missing name'.format(manga['id']))

        return results

    def get_most_populars(self, ratings=None, statuses=None, publication_demographics=None, tags=None, tags_mode=None):
        return self.search(
            None,
            ratings=ratings,
            statuses=statuses,
            publication_demographics=publication_demographics,
            tags=tags,
            tags_mode=tags_mode,
            orderby='populars'
        )

    def resolve_chapters(self, manga_slug):
        chapters = []
        offset = 0

        while True:
            r = self.session_get(self.api_chapter_base, params={
                'manga': manga_slug,
                'translatedLanguage[]': [self.lang_code],
                'limit': CHAPTERS_PER_REQUEST,
                'offset': offset,
                'order[chapter]': 'asc',
                'includes[]': ['scanlation_group'],
                'contentRating[]': ['safe', 'suggestive', 'erotica', 'pornographic'],
            })
            if r.status_code == 204:
                break
            if r.status_code != 200:
                return None

            results = r.json()['data']

            for chapter in results:
                attributes = chapter['attributes']

                title = f'#{attributes["chapter"]}'
                if attributes['title']:
                    title = f'{title} - {attributes["title"]}'

                scanlators = [rel['attributes']['name'] for rel in chapter['relationships'] if rel['type'] == 'scanlation_group']

                data = dict(
                    slug=chapter['id'],
                    title=title,
                    date=convert_date_string(attributes['publishAt'].split('T')[0], format='%Y-%m-%d'),
                    scanlators=scanlators,
                )
                chapters.append(data)

            if len(results) < CHAPTERS_PER_REQUEST:
                break

            offset += CHAPTERS_PER_REQUEST

        return chapters

    def search(self, term, ratings=None, statuses=None, publication_demographics=None, tags=None, tags_mode=None, orderby=None):
        params = {
            'limit': SEARCH_RESULTS_LIMIT,
            'contentRating[]': ratings,
            'status[]': statuses,
            'includes[]': ['cover_art', ],
            'includedTags[]': tags,
            'includedTagsMode': tags_mode,
            'publicationDemographic[]': publication_demographics,
            'availableTranslatedLanguage[]': [self.lang_code, ],
        }
        if orderby == 'latest':
            params['order[latestUploadedChapter]'] = 'desc'
        elif orderby == 'populars':
            params['order[followedCount]'] = 'desc'
        else:
            params['order[title]'] = 'asc'

        if term:
            params['title'] = term

        r = self.session_get(self.api_manga_base, params=params)
        if r.status_code != 200:
            return None

        results = []
        for item in r.json()['data']:
            name = self.__get_manga_title(item['attributes'])

            cover = None
            for relationship in item['relationships']:
                if relationship['type'] == 'cover_art':
                    cover = self.cover_url.format(item['id'], relationship['attributes']['fileName'])
                    break

            if name:
                results.append(dict(
                    slug=item['id'],
                    name=name,
                    cover=cover,
                ))
            else:
                logger.warning('Ignoring result {}, missing name'.format(item['id']))

        return results


class Mangadex_cs(Mangadex):
    id = 'mangadex_cs'
    name = SERVER_NAME
    lang = 'cs'
    lang_code = 'cs'


class Mangadex_de(Mangadex):
    id = 'mangadex_de'
    name = SERVER_NAME
    lang = 'de'
    lang_code = 'de'


class Mangadex_es(Mangadex):
    id = 'mangadex_es'
    name = SERVER_NAME
    lang = 'es'
    lang_code = 'es'


class Mangadex_es_419(Mangadex):
    id = 'mangadex_es_419'
    name = SERVER_NAME
    lang = 'es_419'
    lang_code = 'es-la'


class Mangadex_fr(Mangadex):
    id = 'mangadex_fr'
    name = SERVER_NAME
    lang = 'fr'
    lang_code = 'fr'


class Mangadex_id(Mangadex):
    id = 'mangadex_id'
    name = SERVER_NAME
    lang = 'id'
    lang_code = 'id'


class Mangadex_it(Mangadex):
    id = 'mangadex_it'
    name = SERVER_NAME
    lang = 'it'
    lang_code = 'it'


class Mangadex_ja(Mangadex):
    id = 'mangadex_ja'
    name = SERVER_NAME
    lang = 'ja'
    lang_code = 'ja'


class Mangadex_ko(Mangadex):
    id = 'mangadex_ko'
    name = SERVER_NAME
    lang = 'ko'
    lang_code = 'kr'


class Mangadex_nl(Mangadex):
    id = 'mangadex_nl'
    name = SERVER_NAME
    lang = 'nl'
    lang_code = 'nl'


class Mangadex_pl(Mangadex):
    id = 'mangadex_pl'
    name = SERVER_NAME
    lang = 'pl'
    lang_code = 'pl'


class Mangadex_pt(Mangadex):
    id = 'mangadex_pt'
    name = SERVER_NAME
    lang = 'pt'
    lang_code = 'pt'


class Mangadex_pt_br(Mangadex):
    id = 'mangadex_pt_br'
    name = SERVER_NAME
    lang = 'pt_BR'
    lang_code = 'pt-br'


class Mangadex_ru(Mangadex):
    id = 'mangadex_ru'
    name = SERVER_NAME
    lang = 'ru'
    lang_code = 'ru'


class Mangadex_th(Mangadex):
    id = 'mangadex_th'
    name = SERVER_NAME
    lang = 'th'
    lang_code = 'th'


class Mangadex_uk(Mangadex):
    id = 'mangadex_uk'
    name = SERVER_NAME
    lang = 'uk'
    lang_code = 'uk'


class Mangadex_vi(Mangadex):
    id = 'mangadex_vi'
    name = SERVER_NAME
    lang = 'vi'
    lang_code = 'vi'


class Mangadex_zh_hans(Mangadex):
    id = 'mangadex_zh_hans'
    name = SERVER_NAME
    lang = 'zh_Hans'
    lang_code = 'zh'


class Mangadex_zh_hant(Mangadex):
    id = 'mangadex_zh_hant'
    name = SERVER_NAME
    lang = 'zh_Hant'
    lang_code = 'zh-hk'
