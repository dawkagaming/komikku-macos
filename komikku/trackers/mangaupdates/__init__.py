# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import requests

from komikku.consts import USER_AGENT
from komikku.trackers import authenticated
from komikku.trackers import Tracker

# https://api.mangaupdates.com/


class Mangaupdates(Tracker):
    id = 'mangaupdates'
    name = 'MangaUpdates'

    base_url = 'https://www.mangaupdates.com'
    api_url = 'https://api.mangaupdates.com/v1'
    api_login_url = api_url + '/account/login'
    api_search_url = api_url + '/series/search'
    api_manga_url = api_url + '/series/{0}'
    api_list_add_url = api_url + '/lists/series'
    api_list_update_url = api_url + '/lists/series/update'
    api_manga_list_url = api_url + '/lists/series/{0}'
    api_manga_rating_url = api_url + '/series/{0}/rating'

    STATUSES_MAPPING = {
        # tracker status (list) => internal status
        'read': 'reading',
        'complete': 'completed',
        'hold': 'on_hold',
        'unfinished': 'dropped',
        'wish': 'plan_to_read',
    }

    STATUSES_ID_MAPPING = {
        # internal status => tracker status id (list id)
        'reading': 0,
        'completed': 2,
        'on_hold': 4,
        'dropped': 3,
        'plan_to_read': 1,
    }

    USER_SCORE_FORMAT = {
        'min': 0,
        'max': 10,
        'step': .1,
        'raw_factor': 1,
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def get_manga_url(self, id):
        return None

    def get_tracker_manga_data(self, id):
        # Get serie info
        r = self.session.get(self.api_manga_url.format(id))
        if r.status_code != 200:
            return None

        data = r.json()

        return {
            'id': data['series_id'],
            'name': data['title'],
            'chapters': data['latest_chapter'],
            'score_format': None,
            'url': data['url'],
        }

    def get_user_score_format(self, format):
        return self.USER_SCORE_FORMAT

    @authenticated
    def get_user_manga_data(self, id, access_token=None):
        # Get user serie info: status, chapters progress
        r = self.session_get(
            self.api_manga_list_url.format(id),
            headers={
                'Authorization': f'Bearer {access_token}',
            }
        )
        if r.status_code != 200:
            return None

        resp_data = r.json()

        # Get serie info
        data = self.get_tracker_manga_data(id)
        if data is None:
            return None

        serie_status = None
        for status, list_id in self.STATUSES_ID_MAPPING.items():
            if list_id == resp_data['list_id']:
                serie_status = status
                break

        if serie_status is None:
            return None

        data.update({
            'chapters_progress': resp_data['status']['chapter'],
            'status': serie_status,
        })

        # Get user serie score
        r = self.session_get(
            self.api_manga_rating_url.format(id),
            headers={
                'Authorization': f'Bearer {access_token}',
            }
        )
        data['score'] = r.json()['rating'] if r.status_code == 200 else 0

        return data

    def refresh_access_token(self):
        # Access token can't be refreshed
        # Tracker server don't store the access token
        return None

    def request_access_token(self, username, password):
        r = self.session_put(
            self.api_login_url,
            data={
                'username': username,
                'password': password,
            }
        )
        if r.status_code != 200:
            return False, 'failed'

        data = r.json()
        if data['status'] != 'success':
            return False, 'failed'

        self.data = {
            'access_token': data['context']['session_token'],
            'refresh_token': None,
        }

        return True, None

    def search(self, term):
        r = self.session.post(
            self.api_search_url,
            data={
                'search': term,
            }
        )
        if r.status_code != 200:
            return None

        results = []
        for item in r.json()['results']:
            record = item['record']
            results.append({
                'id': record['series_id'],
                'cover': record['image']['url']['thumb'],
                'name': record['title'],
                'score': record['bayesian_rating'],
                'start_date': record['year'],
                'synopsis': record['description'],
            })

        return results

    @authenticated
    def update_user_manga_data(self, id, data, access_token=None):
        # Check if serie is already in a list
        r = self.session_get(
            self.api_manga_list_url.format(id),
            headers={
                'Authorization': f'Bearer {access_token}',
            }
        )

        if r.status_code == 200:
            # Update
            r = self.session_post(
                self.api_list_update_url,
                json=[{
                    'series': {
                        'id': id,
                    },
                    'list_id': self.STATUSES_ID_MAPPING[data['status']],
                    'status': {
                        'chapter': int(data['chapters_progress']),
                    }
                }],
                headers={
                    'Authorization': f'Bearer {access_token}',
                }
            )

        elif r.status_code == 404:
            # Add
            r = self.session_post(
                self.api_list_add_url,
                json=[
                    {
                        'series': {
                            'id': id,
                        },
                        'list_id': self.STATUSES_ID_MAPPING[data['status']],
                        'status': {
                            'volume': 1,
                            'chapter': int(data['chapters_progress']),
                            'increment_volume': 0,
                            'increment_chapter': 0,
                        },
                        'priority': 0,
                    }
                ],
                headers={
                    'Authorization': f'Bearer {access_token}',
                }
            )

        else:
            return False

        if r.status_code != 200:
            return False

        # Update score
        r = self.session_put(
            self.api_manga_rating_url.format(id),
            data={
                'rating': data['score'],
            },
            headers={
                'Authorization': f'Bearer {access_token}',
            }
        )

        if r.status_code != 200:
            return False

        return True
