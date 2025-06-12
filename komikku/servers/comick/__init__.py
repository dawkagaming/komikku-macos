# SPDX-FileCopyrightText: 2025 gondolyr <gondolyr+code@posteo.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Author: gondolyr <gondolyr+code@posteo.org>

#
# API doc: https://api.comick.fun/docs/
#

import html
import logging

import requests

from komikku.servers import USER_AGENT, Server
from komikku.servers.exceptions import NotFoundError
from komikku.servers.utils import convert_date_string
from komikku.utils import get_buffer_mime_type
from komikku.webview import CompleteChallenge

logger = logging.getLogger("komikku.servers.comick")

SERVER_NAME = "ComicK"

CHAPTERS_PER_REQUEST = 100
SEARCH_RESULTS_LIMIT = 50


class Comick(Server):
    id = "comick"
    name = SERVER_NAME
    lang = "en"
    lang_code = "en"

    has_cf = True
    is_nsfw = False
    is_nsfw_only = False
    long_strip_genres = []

    base_url = "https://comick.io"
    logo_url = base_url + "/favicon.ico"
    api_base_url = "https://api.comick.fun"
    api_manga_base = api_base_url + "/comic"
    api_manga_url = api_manga_base + "/{hid}"
    api_manga_chapters_url = api_manga_url + "/chapters"
    api_chapter_base = api_base_url + "/chapter"
    api_chapter_url = api_chapter_base + "/{hid}"
    api_author_base = api_base_url + "/people"
    api_scanlator_base = api_base_url + "/group"

    manga_url = base_url + "/comic/{slug}"
    api_page_image_url = api_chapter_url + "/get_images"
    image_url = "https://meo.comick.pictures/{b2key}"

    def __init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({"User-Agent": USER_AGENT})

    def _resolve_chapters(self, comic_hid: str) -> list[dict[str, str]]:
        chapters = []
        page = 1

        comic_chapters_url = self.api_manga_chapters_url.format(hid=comic_hid)

        while True:
            r = self.session_get(
                comic_chapters_url,
                params={
                    "limit": CHAPTERS_PER_REQUEST,
                    "page": page,
                    "chap-order": 1,
                    "lang": self.lang_code,
                },
            )
            if r.status_code != 200:
                return None

            r_json = r.json()
            results = r_json["chapters"]
            for chapter in results:
                title = ""
                if chapter["vol"]:
                    title += f'[{chapter["vol"]}] '
                if chapter["chap"]:
                    title += f'#{chapter["chap"]} '
                if chapter["title"]:
                    title += f'- {chapter["title"]}'

                scanlators = chapter["group_name"]

                data = {
                    "slug": chapter["hid"],
                    "title": title,
                    "num": chapter["chap"],
                    "num_volume": chapter["vol"],
                    "date": convert_date_string(
                        chapter["created_at"].split("T")[0], format="%Y-%m-%d"
                    ),
                    "scanlators": scanlators,
                }
                chapters.append(data)

            if len(chapters) == r_json["total"]:
                break

            page += 1

        return chapters

    @CompleteChallenge()
    def get_manga_data(self, initial_data: dict) -> dict:
        """
        Return manga data from the API.

        :param initial_data: Contains the following fields:
            - slug
            - name
            - url
            - last_read
        """
        assert "slug" in initial_data, "Slug is missing in initial data"

        r = self.session_get(self.api_manga_url.format(hid=initial_data["slug"]))
        if r.status_code != 200:
            return None
        resp_json = r.json()

        data = initial_data.copy()
        data.update(
            {
                "authors": [],
                "scanlators": [],
                "genres": [],
                "status": None,
                "cover": None,
                "synopsis": None,
                "chapters": [],
                "server_id": self.id,
            }
        )

        comic_data = resp_json["comic"]

        data["name"] = html.unescape(comic_data["title"])
        assert data["name"] is not None

        data["authors"] = [author["name"] for author in resp_json["authors"]]

        # Always grab the last cover.
        data["cover"] = self.image_url.format(
            b2key=comic_data["md_covers"][-1]["b2key"]
        )

        data["genres"] = [
            genre["md_genres"]["name"] for genre in comic_data["md_comic_md_genres"]
        ]

        match comic_data["status"]:
            case 1:
                # Ongoing.
                data["status"] = "ongoing"
            case 2:
                # Completed.
                data["status"] = "complete"
            case 3:
                # Cancelled.
                data["status"] = "suspended"
            case 4:
                # Hiatus.
                data["status"] = "hiatus"
            case _:
                data["status"] = None

        data["synopsis"] = html.unescape(comic_data["desc"])

        data["chapters"] += self._resolve_chapters(comic_data["hid"])

        return data

    @CompleteChallenge()
    def get_manga_chapter_data(
        self,
        manga_slug: str,
        manga_name: str,
        chapter_slug: str,
        chapter_url: str,
    ) -> dict:
        """
        Return manga chapter data from the API.
        """
        r = self.session_get(self.api_chapter_url.format(hid=chapter_slug))
        if r.status_code == 404:
            raise NotFoundError
        if r.status_code != 200:
            return None

        json_data = r.json()
        chapter_data = json_data["chapter"]

        title = ""
        if chapter_data["vol"]:
            title += f'[{chapter_data["vol"]}] '
        if chapter_data["chap"]:
            title += f'#{chapter_data["chap"]} '
        if chapter_data["title"]:
            title += f'- {chapter_data["title"]}'

        pages = [
            {
                "name": page["name"],
                "slug": page["b2key"],
                "image": None,
            }
            for page in chapter_data["md_images"]
        ]

        scanlators = chapter_data["group_name"]

        return {
            "num": chapter_data["chap"],
            "num_volume": chapter_data["vol"],
            "title": title,
            "pages": pages,
            "date": convert_date_string(
                chapter_data["publish_at"].split("T")[0], format="%Y-%m-%d"
            ),
            "scanlators": scanlators,
        }

    def get_manga_chapter_page_image(
        self, manga_slug: str, manga_name: str, chapter_slug: str, page: dict
    ) -> dict:
        """
        Return chapter page scan (image) content.
        """
        r = self.session_get(self.image_url.format(b2key=page["slug"]))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith("image"):
            return None

        return {
            "buffer": r.content,
            "mime_type": mime_type,
            "name": page["slug"],
        }

    def get_manga_url(self, slug: str, url: str) -> str:
        """
        Return manga absolute URL.
        """
        return self.manga_url.format(slug=slug)

    @CompleteChallenge()
    def get_latest_updates(
        self,
        ratings: list[str] | None = None,
        statuses: list[str] | None = None,
        publication_demographics: int | None = None,
        tags: list[str] | None = None,
        genres: list[str] | None = None,
        tags_mode: list[str] | None = None,
    ) -> list[dict]:
        params = {
            "lang": [self.lang_code],
            "order": "new",
            "type": [
                "manga",
                "manhwa",
                "manhua",
            ],
        }

        r = self.session_get(self.api_chapter_base, params=params)
        if r.status_code != 200:
            return None
        data = r.json()

        # Use a dictionary to only have unique entries and to store the comic attributes.
        comics = {}
        for chapter in data:
            comic_data = chapter["md_comics"]

            if comic_data["title"]:
                comics[comic_data["id"]] = {
                    "slug": comic_data["slug"],
                    "name": comic_data["title"],
                    "cover": self.image_url.format(
                        b2key=comic_data["md_covers"][-1]["b2key"]
                    ),
                }
            else:
                logger.warning(
                    "Ignoring result {}, missing name".format(comic_data["id"])
                )

        return list(comics.values())

    @CompleteChallenge()
    def get_most_populars(
        self,
        ratings: list[str] | None = None,
        statuses: list[str] | None = None,
        publication_demographics: int | None = None,
        tags: list[str] | None = None,
        genres: list[str] | None = None,
        tags_mode: list[str] | None = None,
    ) -> list[dict]:
        return self.search(
            None,
            ratings=ratings,
            statuses=statuses,
            publication_demographics=publication_demographics,
            tags=tags,
            genres=genres,
            tags_mode=tags_mode,
            orderby="view",
        )

    @CompleteChallenge()
    def search(
        self,
        term,
        ratings: list[str] | None = None,
        statuses: list[str] | None = None,
        publication_demographics: int | None = None,
        tags: list[str] | None = None,
        genres: list[str] | None = None,
        tags_mode: str | None = None,
        orderby: str | None = None,
    ) -> list[dict]:
        params = {
            "genres[]": genres,
            "tags[]": tags,
            "demographic[]": publication_demographics,
            "limit": SEARCH_RESULTS_LIMIT,
        }

        if statuses:
            # The API only accepts one status.
            params["status"] = statuses[0]

        if ratings:
            # The API only accepts one content rating.
            params["content_ratings"] = ratings[0]

        if orderby:
            params["sort"] = orderby
        else:
            params["sort"] = "view"

        if term:
            params["q"] = term

        r = self.session_get(f"{self.api_base_url}/v1.0/search", params=params)
        if r.status_code != 200:
            return None
        r_json = r.json()

        results = []
        for comic in r_json:
            if comic["title"]:
                results.append(
                    {
                        "slug": comic["slug"],
                        "name": comic["title"],
                        "cover": self.image_url.format(
                            b2key=comic["md_covers"][-1]["b2key"]
                        ),
                    }
                )
            else:
                logger.warning("Ignoring result {}, missing name".format(comic["id"]))

        return results


class Comick_cs(Comick):
    id = "comick_cs"
    name = SERVER_NAME
    lang = "cs"
    lang_code = "cs"


class Comick_de(Comick):
    id = "comick_de"
    name = SERVER_NAME
    lang = "de"
    lang_code = "de"


class Comick_es(Comick):
    id = "comick_es"
    name = SERVER_NAME
    lang = "es"
    lang_code = "es"


class ComicK_esk419(Comick):
    id = "comick_es_419"
    name = SERVER_NAME
    lang = "es_419"
    lang_code = "es-la"


class Comick_fr(Comick):
    id = "comick_fr"
    name = SERVER_NAME
    lang = "fr"
    lang_code = "fr"


class Comick_id(Comick):
    id = "comick_id"
    name = SERVER_NAME
    lang = "id"
    lang_code = "id"


class Comick_it(Comick):
    id = "comick_it"
    name = SERVER_NAME
    lang = "it"
    lang_code = "it"


class Comick_ja(Comick):
    id = "comick_ja"
    name = SERVER_NAME
    lang = "ja"
    lang_code = "ja"


class Comick_ko(Comick):
    id = "comick_ko"
    name = SERVER_NAME
    lang = "ko"
    lang_code = "kr"


class Comick_nl(Comick):
    id = "comick_nl"
    name = SERVER_NAME
    lang = "nl"
    lang_code = "nl"


class Comick_pl(Comick):
    id = "comick_pl"
    name = SERVER_NAME
    lang = "pl"
    lang_code = "pl"


class Comick_pt(Comick):
    id = "comick_pt"
    name = SERVER_NAME
    lang = "pt"
    lang_code = "pt"


class ComicK_pk_br(Comick):
    id = "comick_pt_br"
    name = SERVER_NAME
    lang = "pt_BR"
    lang_code = "pt-br"


class Comick_ru(Comick):
    id = "comick_ru"
    name = SERVER_NAME
    lang = "ru"
    lang_code = "ru"


class Comick_th(Comick):
    id = "comick_th"
    name = SERVER_NAME
    lang = "th"
    lang_code = "th"


class Comick_uk(Comick):
    id = "comick_uk"
    name = SERVER_NAME
    lang = "uk"
    lang_code = "uk"


class Comick_vi(Comick):
    id = "comick_vi"
    name = SERVER_NAME
    lang = "vi"
    lang_code = "vi"


class ComicK_zh_kans(Comick):
    id = "comick_zh_hans"
    name = SERVER_NAME
    lang = "zh_Hans"
    lang_code = "zh"


class ComicK_zh_kant(Comick):
    id = "comick_zh_hant"
    name = SERVER_NAME
    lang = "zh_Hant"
    lang_code = "zh-hk"
