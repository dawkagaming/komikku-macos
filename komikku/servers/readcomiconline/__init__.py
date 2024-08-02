# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import base64
from bs4 import BeautifulSoup
import logging
from urllib.parse import unquote

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type
from komikku.webview import CompleteChallenge

logger = logging.getLogger('komikku.servers.readcomiconline')


class Readcomiconline(Server):
    id = 'readcomiconline'
    name = 'Read Comic Online'
    lang = 'en'
    is_nsfw = True

    has_cf = True

    base_url = 'https://readcomiconline.li'
    latest_updates_url = base_url + '/ComicList/LatestUpdate'
    most_populars_url = base_url + '/ComicList/MostPopular'
    search_url = base_url + '/AdvanceSearch'
    manga_url = base_url + '/Comic/{0}'
    chapter_url = base_url + '/Comic/{0}/{1}?readType=1'
    bypass_cf_url = base_url + '/ComicList'

    # To be sure that HTML pages are not rendered in mobile version
    headers = {
        'User-Agent': USER_AGENT,  # used in @BypassCF when session is created
    }

    def __init__(self):
        self.session = None

    @CompleteChallenge()
    def get_manga_data(self, initial_data):
        """
        Returns comic data by scraping manga HTML page content

        Initial data should contain at least comic's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug'], 1))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],  # not available
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        soup = BeautifulSoup(r.text, 'lxml')

        info_element = soup.select_one('#leftside .barContent')

        data['name'] = info_element.select_one('.bigChar').text.strip()
        cover_path = soup.select_one('#rightside img').get('src')
        if cover_path.startswith('http'):
            data['cover'] = cover_path
        else:
            data['cover'] = '{0}{1}'.format(self.base_url, cover_path)

        for p_element in info_element.select('p'):
            if not p_element.span:
                if not data['synopsis']:
                    data['synopsis'] = p_element.text.strip()
                continue

            span_element = p_element.span.extract()
            label = span_element.text.strip()

            if label.startswith('Genres'):
                data['genres'] = [a_element.text.strip() for a_element in p_element.select('a')]

            elif label.startswith(('Writer', 'Artist')):
                for a_element in p_element.select('a'):
                    value = a_element.text.strip()
                    if value not in data['authors']:
                        data['authors'].append(value)

            elif label.startswith('Status'):
                value = p_element.text.strip()
                if 'Completed' in value:
                    data['status'] = 'complete'
                elif 'Ongoing' in value:
                    data['status'] = 'ongoing'

        # Chapters (Issues)
        for tr_element in reversed(soup.select('.listing tr')):
            td_elements = tr_element.select('td')
            if not td_elements:
                continue

            data['chapters'].append(dict(
                slug=td_elements[0].a.get('href').split('?')[0].split('/')[-1],
                title=td_elements[0].a.text.strip(),
                date=convert_date_string(td_elements[1].text.strip(), format='%m/%d/%Y'),
            ))

        return data

    @CompleteChallenge()
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns comic chapter data
        """
        def decode_url(url, server):
            # Scripts/rguard.min.js?v=1.5.1
            url = url.replace('pw_.g28x', 'b').replace('d2pr.x_27', 'h')

            if not url.startswith('https'):
                if '?' in url:
                    url, qs = url.split('?')
                else:
                    qs = None

                if '=s0' in url:
                    url = url.replace('=s0', '')
                    s = '=s0'
                elif '=s1600' in url:
                    url = url.replace('=s1600', '')
                    s = '=s1600'

                url = url[15:33] + url[50:]
                url = url[0:len(url) - 11] + url[len(url) - 2] + url[len(url) - 1]
                url = unquote(unquote(base64.b64decode(url)))
                url = 'https://2.bp.blogspot.com/' + url[0:13] + url[17:-2] + s
                if qs:
                    url += '?' + qs

            if server:
                url = url.replace('https://2.bp.blogspot.com', server)

            return url

        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        encoded_urls = []
        media_server = None
        for script_element in soup.select('script'):
            script = script_element.string
            if not script or 'lstImages' not in script:
                continue

            for line in script.split('\n'):
                line = line.strip()
                if line.startswith('var pth'):
                    pth = line[11:-2]
                    pth = pth.replace('v6f5S__YOy__', 'g')
                    pth = pth.replace('pVse_m__Vd9', 'd')
                    pth = pth.replace('b', 'pw_.g28x')
                    pth = pth.replace('h', 'd2pr.x_27')

                    encoded_urls.append(pth)
                elif line.startswith('beau'):
                    media_server = line[17:-3]
            break

        data = dict(
            pages=[],
        )

        for index, url in enumerate(encoded_urls):
            data['pages'].append(dict(
                image=decode_url(url, media_server),
                slug=None,
                index=index + 1,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=f"{page['index']}.{mime_type.split('/')[1]}",
        )

    def get_manga_url(self, slug, url):
        """
        Returns comic absolute URL
        """
        return self.manga_url.format(slug)

    @CompleteChallenge()
    def get_manga_list(self, term=None, orderby=None):
        results = []

        if term:
            r = self.session_get(
                self.search_url,
                params=dict(
                    comicName=term,
                    ig='',
                    eg='',
                    status='',
                    pubDate='',
                ),
                headers={
                    'Referer': self.search_url,
                }
            )
        elif orderby == 'populars':
            r = self.session_get(self.most_populars_url)
        elif orderby == 'latest':
            r = self.session_get(self.latest_updates_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        for a_element in soup.select('.item > a:first-child'):
            if not a_element.get('href'):
                continue

            cover = a_element.img.get('src')
            if not cover.startswith('http'):
                cover = self.base_url + cover

            results.append(dict(
                name=a_element.span.text.strip(),
                slug=a_element.get('href').split('/')[-1],
                cover=cover,
            ))

        return results

    def get_latest_updates(self):
        """
        Returns latest updates
        """
        return self.get_manga_list(orderby='latest')

    def get_most_populars(self):
        """
        Returns most popular comics
        """
        return self.get_manga_list(orderby='populars')

    def search(self, term):
        return self.get_manga_list(term=term)
