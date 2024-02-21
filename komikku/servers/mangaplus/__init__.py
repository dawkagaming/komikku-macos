# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import IntEnum
from functools import wraps
import re
from typing import List
import uuid

from pure_protobuf.annotations import Field
from pure_protobuf.message import BaseMessage
import requests
from typing_extensions import Annotated
import unidecode

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import get_buffer_mime_type

LANGUAGES_CODES = dict(
    en='eng',
    es='esp',
    fr='fra',
    pt_BR='ptb',
    ru='rus',
    id='ind',
    th='tha',
    vi='vie',
)
RE_ENCRYPTION_KEY = re.compile('.{1,2}')
SERVER_NAME = 'MANGA Plus by SHUEISHA'

headers = {
    'User-Agent': USER_AGENT,
    'Origin': 'https://mangaplus.shueisha.co.jp',
    'Referer': 'https://mangaplus.shueisha.co.jp',
    'SESSION-TOKEN': repr(uuid.uuid1()),
}


def set_lang(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        server = args[0]
        if not server.is_lang_set:
            server.session_get(server.api_params_url, params=dict(lang=LANGUAGES_CODES[server.lang]))
            server.is_lang_set = True

        return func(*args, **kwargs)

    return wrapper


class Mangaplus(Server):
    id = 'mangaplus'
    name = SERVER_NAME
    lang = 'en'

    is_lang_set = False

    base_url = 'https://mangaplus.shueisha.co.jp'
    api_url = 'https://jumpg-webapi.tokyo-cdn.com/api'
    api_params_url = api_url + '/featured'
    api_search_url = api_url + '/title_list/all'
    api_latest_updates_url = api_url + '/web/web_home?lang={0}'
    api_most_populars_url = api_url + '/title_list/ranking'
    api_manga_url = api_url + '/title_detail?title_id={0}'
    api_chapter_url = api_url + '/manga_viewer?chapter_id={0}&split=yes&img_quality=high'
    manga_url = base_url + '/titles/{0}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = headers

    @set_lang
    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.api_manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'application/octet-stream':
            return None

        resp = MangaplusResponse.loads(r.content)
        if resp.error:
            return None

        resp_data = resp.success.title_detail

        data = initial_data.copy()
        data.update(dict(
            name=resp_data.title.name,
            authors=[resp_data.title.author],
            scanlators=['Shueisha'],
            genres=[],
            status=None,
            synopsis=resp_data.synopsis,
            chapters=[],
            server_id=self.id,
            cover=resp_data.title.portrait_image_url,
        ))

        # Status
        if 'completed' in resp_data.non_appearance_info or 'completado' in resp_data.non_appearance_info:
            data['status'] = 'complete'
        else:
            data['status'] = 'ongoing'

        # Chapters
        for chapters in (resp_data.first_chapters, resp_data.last_chapters):
            for chapter in chapters:
                data['chapters'].append(dict(
                    slug=str(chapter.id),
                    title='{0} - {1}'.format(chapter.name, chapter.subtitle),
                    date=datetime.fromtimestamp(chapter.start_timestamp).date(),
                ))

        return data

    @set_lang
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data from API

        Currently, only pages are expected.
        """
        r = self.session_get(self.api_chapter_url.format(chapter_slug))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'application/octet-stream':
            return None

        resp = MangaplusResponse.loads(r.content)
        if resp.error:
            return None

        resp_data = resp.success.manga_viewer

        data = dict(
            pages=[],
        )
        for page in resp_data.pages:
            if page.page is None:
                continue

            data['pages'].append(dict(
                slug=None,
                image=page.page.image_url,
                encryption_key=page.page.encryption_key,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
        if r.status_code != 200:
            return None

        if page['encryption_key'] is not None:
            # Decryption
            key_stream = [int(v, 16) for v in RE_ENCRYPTION_KEY.findall(page['encryption_key'])]
            block_size_in_bytes = len(key_stream)

            content = bytes([int(v) ^ key_stream[index % block_size_in_bytes] for index, v in enumerate(r.content)])
        else:
            content = r.content

        mime_type = get_buffer_mime_type(content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=content,
            mime_type=mime_type,
            name=page['image'].split('?')[0].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    @set_lang
    def get_latest_updates(self):
        """
        Returns latest updates
        """
        r = self.session_get(self.api_latest_updates_url.format(LANGUAGES_CODES[self.lang]))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'application/octet-stream':
            return None

        resp_data = MangaplusResponse.loads(r.content)
        if resp_data.error:
            return None

        results = []
        for group in resp_data.success.web_home_view.update_title_groups:
            for update_title in group.titles:
                title = update_title.title
                if title.language != LanguageEnum.from_code(self.lang):
                    continue

                results.append(dict(
                    slug=title.id,
                    name=title.name,
                    cover=title.portrait_image_url,
                ))

        return results

    @set_lang
    def get_most_populars(self):
        """
        Returns hottest manga list
        """
        r = self.session_get(self.api_most_populars_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'application/octet-stream':
            return None

        resp_data = MangaplusResponse.loads(r.content)
        if resp_data.error:
            return None

        results = []
        for title in resp_data.success.titles_ranking.titles:
            if title.language != LanguageEnum.from_code(self.lang):
                continue

            results.append(dict(
                slug=title.id,
                name=title.name,
                cover=title.portrait_image_url,
            ))

        return results

    @set_lang
    def search(self, term):
        r = self.session_get(self.api_search_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'application/octet-stream':
            return None

        resp_data = MangaplusResponse.loads(r.content)
        if resp_data.error:
            return None

        results = []
        term = unidecode.unidecode(term).lower()
        for title in resp_data.success.titles_all.titles:
            if title.language != LanguageEnum.from_code(self.lang):
                continue
            if term not in unidecode.unidecode(title.name).lower():
                continue

            results.append(dict(
                slug=title.id,
                name=title.name,
                cover=title.portrait_image_url,
            ))

        return results


class Mangaplus_es(Mangaplus):
    id = 'mangaplus_es'
    name = SERVER_NAME
    lang = 'es'


class Mangaplus_fr(Mangaplus):
    id = 'mangaplus_fr'
    name = SERVER_NAME
    lang = 'fr'


class Mangaplus_id(Mangaplus):
    id = 'mangaplus_id'
    name = SERVER_NAME
    lang = 'id'


class Mangaplus_pt_br(Mangaplus):
    id = 'mangaplus_pt_br'
    name = SERVER_NAME
    lang = 'pt_BR'


class Mangaplus_ru(Mangaplus):
    id = 'mangaplus_ru'
    name = SERVER_NAME
    lang = 'ru'


class Mangaplus_th(Mangaplus):
    id = 'mangaplus_th'
    name = SERVER_NAME
    lang = 'th'


class Mangaplus_vi(Mangaplus):
    id = 'mangaplus_vi'
    name = SERVER_NAME
    lang = 'vi'


# Protocol Buffers messages used to deserialize API responses
# https://gist.github.com/ZaneHannanAU/437531300c4df524bdb5fd8a13fbab50

class ActionEnum(IntEnum):
    DEFAULT = 0
    UNAUTHORIZED = 1
    MAINTAINENCE = 2
    GEOIP_BLOCKING = 3


class LanguageEnum(IntEnum):
    ENGLISH = 0
    SPANISH = 1
    FRENCH = 2
    INDONESIAN = 3
    PORTUGUESE_BR = 4
    RUSSIAN = 5
    THAI = 6
    VIET = 9

    @classmethod
    def from_code(cls, code):
        # MUST BE kept in sync with `LANGUAGES_CODES` defined above
        if code == 'en':
            return cls.ENGLISH.value
        if code == 'es':
            return cls.SPANISH.value
        if code == 'fr':
            return cls.FRENCH.value
        if code == 'id':
            return cls.INDONESIAN.value
        if code == 'pt_BR':
            return cls.PORTUGUESE_BR.value
        if code == 'ru':
            return cls.RUSSIAN.value
        if code == 'th':
            return cls.THAI.value
        if code == 'vi':
            return cls.VIET.value


class UpdateTimingEnum(IntEnum):
    NOT_REGULARLY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7
    DAY = 8


@dataclass
class Popup(BaseMessage):
    subject: Annotated[str, Field(1)]
    body: Annotated[str, Field(2)]


@dataclass
class ErrorResult(BaseMessage):
    action: Annotated[ActionEnum, Field(1)]
    english_popup: Annotated[Popup, Field(2)]
    spanish_popup: Annotated[Popup, Field(3)]
    debug_info: Annotated[str, Field(4)]


@dataclass
class MangaPage(BaseMessage):
    image_url: Annotated[str, Field(1)]
    width: Annotated[int, Field(2)]
    height: Annotated[int, Field(3)]
    encryption_key: Annotated[str, Field(5)] = None


@dataclass
class Page(BaseMessage):
    page: Annotated[MangaPage, Field(1)] = None


@dataclass
class MangaViewer(BaseMessage):
    pages: Annotated[List[Page], Field(1)] = field(default_factory=list)


@dataclass
class Chapter(BaseMessage):
    title_id: Annotated[int, Field(1)]
    id: Annotated[int, Field(2)]
    name: Annotated[str, Field(3)]
    subtitle: Annotated[str, Field(4)] = None
    start_timestamp: Annotated[int, Field(6)] = None
    end_timestamp: Annotated[int, Field(7)] = None


@dataclass
class Title(BaseMessage):
    id: Annotated[int, Field(1)]
    name: Annotated[str, Field(2)]
    author: Annotated[str, Field(3)]
    portrait_image_url: Annotated[str, Field(4)]
    # landscape_image_url: Annotated[str, Field(5)]
    # view_count: Annotated[int, Field(6)]
    language: Annotated[LanguageEnum, Field(7)] = LanguageEnum.ENGLISH


@dataclass
class TitleDetail(BaseMessage):
    title: Annotated[Title, Field(1)]
    title_image_url: Annotated[str, Field(2)]
    synopsis: Annotated[str, Field(3)]
    # background_image_url: Annotated[str, Field(4)]
    next_timestamp: Annotated[int, Field(5)] = 0
    update_timimg: Annotated[UpdateTimingEnum, Field(6)] = UpdateTimingEnum.DAY
    viewing_period_description: Annotated[str, Field(7)] = None
    non_appearance_info: Annotated[str, Field(8)] = ''
    first_chapters: Annotated[List[Chapter], Field(9)] = field(default_factory=list)
    last_chapters: Annotated[List[Chapter], Field(10)] = field(default_factory=list)
    is_simul_related: Annotated[bool, Field(14)] = True
    chapters_descending: Annotated[bool, Field(17)] = True


@dataclass
class TitlesAll(BaseMessage):
    titles: Annotated[List[Title], Field(1)]


@dataclass
class TitlesRanking(BaseMessage):
    titles: Annotated[List[Title], Field(1)]


@dataclass
class UpdatedTitle(BaseMessage):
    title: Annotated[Title, Field(1)] = None


@dataclass
class UpdatedTitleGroup(BaseMessage):
    group_name: Annotated[str, Field(1)] = None
    titles: Annotated[List[UpdatedTitle], Field(2)] = field(default_factory=list)


@dataclass
class WebHomeView(BaseMessage):
    update_title_groups: Annotated[List[UpdatedTitleGroup], Field(2)] = field(default_factory=list)


@dataclass
class SuccessResult(BaseMessage):
    is_featured_updated: Annotated[bool, Field(1)] = False
    titles_all: Annotated[TitlesAll, Field(5)] = None
    titles_ranking: Annotated[TitlesRanking, Field(6)] = None
    title_detail: Annotated[TitleDetail, Field(8)] = None
    manga_viewer: Annotated[MangaViewer, Field(10)] = None
    web_home_view: Annotated[WebHomeView, Field(11)] = None


@dataclass
class MangaplusResponse(BaseMessage):
    success: Annotated[SuccessResult, Field(1)] = None
    error: Annotated[ErrorResult, Field(2)] = None
