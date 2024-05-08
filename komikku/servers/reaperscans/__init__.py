# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json
import random
import string

from bs4 import BeautifulSoup
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.multi.heancms import HeanCMS
from komikku.servers.multi.genkan import GenkanInitial
from komikku.servers.multi.madara import Madara
from komikku.servers.utils import convert_date_string
from komikku.servers.utils import get_buffer_mime_type
from komikku.webview import BypassCF


def generate_id():
    """ Generate a random 4-5 alpha-num character string """
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(random.randint(4, 5)))


class Reaperscans(Server):
    id = 'reaperscans'
    name = 'Reaper Scans'
    lang = 'en'

    has_cf = True

    base_url = 'https://reaperscans.com'
    api_url = base_url + '/livewire/message/{0}'
    latest_updates_url = base_url + '/latest/comics'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/chapters/{1}'

    def __init__(self):
        self.session = None

    @BypassCF()
    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content + API for chapters

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = initial_data.copy()
        data.update(dict(
            authors=[],  # not available
            scanlators=[],  # not available
            genres=[],  # not available
            status=None,
            cover=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        data['name'] = soup.select_one('img.h-full.w-full').get('alt').strip()
        data['cover'] = soup.select_one('img.h-full.w-full').get('src')

        # Details
        status = soup.select_one('dt:-soup-contains("Release Status")').parent.select_one('dd').text
        if status == 'On hold':
            data['status'] = 'hiatus'
        elif status == 'Complete':
            data['status'] = 'complete'
        elif status == 'Ongoing':
            data['status'] = 'ongoing'
        elif status == 'Dropped':
            data['status'] = 'Suspended'

        # Synopsis
        data['synopsis'] = soup.select_one('p.prose').text.strip()

        # Chapters
        data['chapters'] = self.get_manga_chapters_data(soup, data['slug'])

        return data

    def get_manga_chapters_data(self, soup, slug):
        csrf_token = None
        data = []
        more = True
        payload = None

        def parse_chapters_page(soup_page):
            data_page = []
            for a_element in soup_page.select('li[wire\\:key^="comic-chapter-list"] > a'):
                p_elements = a_element.select('p')
                data_page.append(dict(
                    slug=a_element.get('href').split('/')[-1],
                    title=p_elements[0].text.strip(),
                    date=convert_date_string(p_elements[1].text.replace('Released', '').strip()),
                ))

            more = soup_page.select_one('button[wire\\:click^="nextPage"]') is not None

            return data_page, more

        while more:
            if csrf_token is None and payload is None:
                csrf_token = soup.select_one('meta[name="csrf-token"]').get('content')

                payload = None
                if element := soup.select_one('[wire\\:initial-data*="frontend.comic-chapter-list"]'):
                    payload = json.loads(element.get('wire:initial-data'))

                if csrf_token is None or payload is None:
                    return None

                payload.pop('effects')
                payload['updates'] = [
                    {
                        'payload': {
                            'id': generate_id(),
                            'method': 'nextPage',
                            'params': ['page'],
                        },
                        'type': 'callMethod',
                    }
                ]

                data_page, more = parse_chapters_page(soup)
            else:
                r = self.session_post(
                    self.api_url.format(payload['fingerprint']['name']),
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'Referer': self.manga_url.format(slug),
                        'X-Csrf-Token': csrf_token,
                        'X-Livewire': 'true',
                    }
                )
                if r.status_code != 200:
                    break

                resp_data = r.json()
                if not resp_data.get('effects'):
                    break

                # Save state
                payload['serverMemo']['checksum'] = resp_data['serverMemo']['checksum']
                payload['serverMemo']['data']['page'] = resp_data['serverMemo']['data']['page']
                payload['serverMemo']['data']['paginators']['page'] = resp_data['serverMemo']['data']['paginators']['page']
                payload['serverMemo']['htmlHash'] = resp_data['serverMemo']['htmlHash']
                payload['updates'][0]['payload']['id'] = generate_id()

                data_page, more = parse_chapters_page(BeautifulSoup(resp_data['effects']['html'], 'lxml'))

            data += data_page

        return reversed(data)

    @BypassCF()
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = dict(
            pages=[],
        )
        for img_element in soup.select('img.max-w-full'):
            if img_element.get('data-lazy-src'):
                url = img_element.get('data-lazy-src')
            elif img_element.get('data-src'):
                url = img_element.get('data-src')
            elif img_element.get('data-cfsrc'):
                url = img_element.get('data-cfsrc')
            else:
                url = img_element.get('src')

            data['pages'].append(dict(
                slug=None,
                image=url,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page['image'],
            headers={
                'Referer': self.chapter_url.format(manga_slug, chapter_slug),
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
            name=page['image'].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    @BypassCF()
    def get_latest_updates(self):
        r = self.session_get(self.latest_updates_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.select('.grid > div'):
            a_element = element.select_one('p > a')
            results.append(dict(
                slug=a_element.get('href').split('/')[-1],
                name=a_element.text.strip(),
                cover=element.select_one('img').get('src'),
            ))

        return results

    @BypassCF()
    def search(self, term):
        r = self.session_get(self.base_url)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        csrf_token = soup.select_one('meta[name="csrf-token"]')['content']

        payload = None
        for element in soup.select('[wire\\:initial-data*="fingerprint"]'):
            data = json.loads(element.get('wire:initial-data'))
            if data['fingerprint'].get('name', '').startswith('frontend'):
                payload = data
                break

        if payload is None:
            return None

        payload.pop('effects')
        payload['updates'] = [
            {
                'type': 'syncInput',
                'payload': {
                    'id': generate_id(),
                    'name': 'query',
                    'value': term,
                }
            }
        ]

        r = self.session_post(
            self.api_url.format(payload['fingerprint']['name']),
            json=payload,
            headers={
                'Referer': f'{self.base_url}/',
                'Content-Type': 'application/json',
                'X-Csrf-Token': csrf_token,
                'X-Livewire': 'true',
            }
        )
        if r.status_code != 200:
            return None

        data = r.json()

        soup = BeautifulSoup(data['effects']['html'], 'lxml')

        results = []
        for a_element in soup.select('a[href*="/comics/"]'):
            img_element = a_element.select_one('img')
            results.append(dict(
                slug=a_element.get('href').split('/')[-1],
                name=img_element.get('alt'),
                cover=img_element.get('src'),
            ))

        return results


class Reaperscans_ar(Madara):
    id = 'reaperscans_ar'
    name = 'ريبر العربي'
    lang = 'ar'

    series_name = 'series'
    date_format = '%Y, %d %B'

    base_url = 'https://reaperscansar.com'
    chapters_url = base_url + '/series/{0}/ajax/chapters/'


class Reaperscans_fr(Madara):
    id = 'reaperscans_fr'
    name = 'ReaperScansFR (GS)'
    lang = 'fr'

    has_cf = True

    series_name = 'serie'
    date_format = '%d/%m/%Y'

    base_url = 'https://reaperscans.fr'

    details_scanlators_selector = '.post-content_item:-soup-contains("Team") .summary-content'


class Reaperscans_id(Madara):
    id = 'reaperscans_id'
    name = 'Reaper Scans'
    lang = 'id'

    series_name = 'series'

    base_url = 'https://reaperscans.id'


class Reaperscans_pt(Server):
    id = 'reaperscans_pt'
    name = 'Reaper Scans'
    lang = 'pt'
    status = 'disabled'  # Switch to HeanCMS (2023-??), a new server has been added with correct language (pt-BR)

    api_base_url = 'https://api.reaperscans.net'
    api_search_url = api_base_url + '/series/search'
    api_most_populars_url = api_base_url + '/series/querysearch'
    api_chapter_url = api_base_url + '/series/chapter/{}'

    base_url = 'https://reaperscans.net'
    manga_url = base_url + '/series/{0}'
    chapter_url = base_url + '/series/{0}/{1}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],  # Not available
            genres=[],
            status=None,    # Not available
            cover=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        data['name'] = soup.find('h1').text.strip()
        data['cover'] = soup.find('img', class_='rounded-thumb').get('src')

        # Details
        data['genres'] = [span.text.strip() for span in soup.find('div', class_='tags-container').find_all('span', class_='tag')]
        data['status'] = 'ongoing'

        container_element = soup.find('div', class_='useful-container')
        for author in container_element.select_one('p:-soup-contains("Autor") strong').text.strip().split(','):
            data['authors'].append(author.strip())

        # Synopsis
        data['synopsis'] = soup.find('div', class_='description-container').text.strip()

        # Chapters
        for a_element in reversed(soup.select('#simple-tabpanel-0 ul > a')):
            data['chapters'].append(dict(
                slug=a_element.get('href').split('/')[-1],
                title=a_element.select_one('.MuiTypography-body1').text.strip(),
                date=convert_date_string(a_element.select_one('.MuiTypography-body2').text.strip(), format='%d/%m/%Y'),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content + API

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        id_ = None
        for script_element in soup.find_all('script'):
            if script_element.get('id') != '__NEXT_DATA__':
                continue
            data = json.loads(script_element.string)
            id_ = data['props']['pageProps']['data']['id']
            break

        if id_ is None:
            return None

        r = self.session_get(self.api_chapter_url.format(id_))
        if r.status_code != 200:
            return None

        data = dict(
            pages=[],
        )
        for image in r.json()['content']['images']:
            data['pages'].append(dict(
                slug=None,
                image=image,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(self.api_base_url + '/' + page['image'])
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['image'].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_latest_updates(self):
        return self.search('', orderby='latest')

    def get_most_populars(self):
        return self.search('', orderby='populars')

    def search(self, term, orderby=None):
        if orderby:
            r = self.session_post(
                self.api_most_populars_url,
                params=dict(
                    order='desc',
                    order_by='total_views' if orderby == 'populars' else 'recently_added',
                    series_type='Comic',
                ),
                headers={
                    'content-type': 'application/json',
                }
            )
        else:
            r = self.session_post(
                self.api_search_url,
                params=dict(
                    term=term,
                ),
                headers={
                    'content-type': 'application/json',
                }
            )
        if r.status_code != 200:
            return None

        items = r.json()
        if orderby:
            items = items['data']

        results = []
        for item in items:
            if item['series_type'] not in ('Comic',):
                continue

            results.append(dict(
                slug=item['series_slug'],
                name=item['title'],
            ))

        return results


class Reaperscans_pt_br(HeanCMS):
    id = 'reaperscans_pt_br'
    name = 'Yugen Scans (Reaper Scans)'
    lang = 'pt_BR'
    status = 'disabled'  # 03/2024: move to https://ikigaimangas.com/

    base_url = 'https://yugenmangas.lat'
    api_url = 'https://api.yugenmangas.net'

    cover_css_path = 'div div div.container.px-5.text-gray-50 div.grid.grid-cols-12.pt-3.gap-x-3 div.col-span-12.relative.flex.justify-center.w-full div.flex.flex-col.items-center.justify-center.gap-y-2.w-full img'
    authors_css_path = 'div div.container.px-5.text-gray-50 div.grid.grid-cols-12.pt-3.gap-x-3 div.col-span-12.flex.flex-col.gap-y-3 div div.flex.flex-col.gap-y-2 p:nth-child(3) strong'
    synopsis_css_path = 'div div.container.px-5.text-gray-50 div.grid.grid-cols-12.pt-3.gap-x-3 div.col-span-12.flex.flex-col.gap-y-3 div.bg-gray-800.text-gray-50.rounded-xl.p-5'


class Reaperscans_tr(Madara):
    id = 'reaperscans_tr'
    name = 'Reaper Scans'
    lang = 'tr'

    series_name = 'seri'

    base_url = 'https://reaperscanstr.com'


class Reaperscans__old(GenkanInitial):
    id = 'reaperscans__old'
    name = 'Reaper Scans'
    lang = 'en'
    status = 'disabled'

    # Use Cloudflare
    # Search is partially broken -> inherit from GenkanInitial instead of Genkan class

    base_url = 'https://reaperscans.com'
    search_url = base_url + '/comics'
    most_populars_url = base_url + '/home'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'
