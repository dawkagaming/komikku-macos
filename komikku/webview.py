# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import inspect
import logging
import os
import platform
import time
import tzlocal

import gi
import requests

gi.require_version('Adw', '1')
gi.require_version('WebKit', '6.0')

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import WebKit

from komikku.servers.exceptions import CfBypassError
from komikku.utils import get_cache_dir

CF_RELOAD_MAX = 3
DEBUG = False

logger = logging.getLogger('komikku.webview')


@Gtk.Template.from_resource('/info/febvre/Komikku/ui/webview.ui')
class WebviewPage(Adw.NavigationPage):
    __gtype_name__ = 'WebviewPage'

    toolbarview = Gtk.Template.Child('toolbarview')
    title = Gtk.Template.Child('title')

    cf_request = None  # Current CF request
    cf_request_handlers_ids = []  # List of hendlers IDs (connected events) of current CF request
    cf_requests = []  # List of pending CF requests
    exited = True  # Whether webview has been exited (page has been popped)
    exited_auto = False  # Whether webview has been automatically left (no user interaction)
    lock = False  # Whether webview is locked (in use)

    def __init__(self, window):
        Adw.NavigationPage.__init__(self)

        self.window = window

        self.connect('hidden', self.on_hidden)

        # User agent: Gnome Web like
        cpu_arch = platform.machine()
        session_type = GLib.getenv('XDG_SESSION_TYPE').capitalize()
        custom_part = f'{session_type}; Linux {cpu_arch}'
        self.user_agent = f'Mozilla/5.0 ({custom_part}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'

        # Settings
        self.settings = WebKit.Settings.new()
        self.settings.set_enable_developer_extras(DEBUG)
        self.settings.set_enable_write_console_messages_to_stdout(DEBUG)
        self.settings.set_enable_dns_prefetching(True)

        # Enable extra features
        all_feature_list = self.settings.get_all_features()
        if DEBUG:
            experimental_feature_list = self.settings.get_experimental_features()
            development_feature_list = self.settings.get_development_features()
            experimental_features = [
                experimental_feature_list.get(index).get_identifier() for index in range(experimental_feature_list.get_length())
            ]
            development_features = [
                development_feature_list.get(index).get_identifier() for index in range(development_feature_list.get_length())
            ]

            # Categories: Security, Animation, JavaScript, HTML, Other, DOM, Privacy, Media, Network, CSS
            for index in range(all_feature_list.get_length()):
                feature = all_feature_list.get(index)
                if feature.get_identifier() in experimental_features:
                    type = 'Experimental'
                elif feature.get_identifier() in development_features:
                    type = 'Development'
                else:
                    type = 'Stable'
                if feature.get_category() == 'Other' and not feature.get_default_value():
                    print('ID: {0}, Default: {1}, Category: {2}, Details: {3}, type: {4}'.format(
                        feature.get_identifier(),
                        feature.get_default_value(),
                        feature.get_category(),
                        feature.get_details(),
                        type
                    ))

        extra_features_enabled = (
            'AllowDisplayOfInsecureContent',
            'AllowRunningOfInsecureContent',
            'JavaScriptCanAccessClipboard',
        )
        for index in range(all_feature_list.get_length()):
            feature = all_feature_list.get(index)
            if feature.get_identifier() in extra_features_enabled and not feature.get_default_value():
                self.settings.set_feature_enabled(feature, True)

        # Context
        self.web_context = WebKit.WebContext(time_zone_override=tzlocal.get_localzone_name())
        self.web_context.set_cache_model(WebKit.CacheModel.DOCUMENT_VIEWER)
        self.web_context.set_preferred_languages(['en-US', 'en'])

        # Network session
        self.network_session = WebKit.NetworkSession.new(
            os.path.join(get_cache_dir(), 'webview', 'data'),
            os.path.join(get_cache_dir(), 'webview', 'cache')
        )
        self.network_session.get_website_data_manager().set_favicons_enabled(True)
        self.network_session.set_itp_enabled(False)
        self.network_session.get_cookie_manager().set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)
        self.network_session.get_cookie_manager().set_persistent_storage(
            os.path.join(get_cache_dir(), 'webview', 'cookies.sqlite'),
            WebKit.CookiePersistentStorage.SQLITE
        )

        # Create Webview
        self.webkit_webview = WebKit.WebView(
            web_context=self.web_context,
            network_session=self.network_session,
            settings=self.settings
        )

        self.toolbarview.set_content(self.webkit_webview)
        self.window.navigationview.add(self)

    def close_page(self, blank=True):
        self.disconnect_all_signals()

        if blank:
            self.webkit_webview.stop_loading()
            GLib.idle_add(self.webkit_webview.load_uri, 'about:blank')

        def do_next():
            if not self.exited:
                return GLib.SOURCE_CONTINUE

            self.lock = False
            self.pop_cf_request()

            return GLib.SOURCE_REMOVE

        if self.cf_request:
            # Wait page is exited to unlock and load next pending CF request (if exists)
            GLib.idle_add(do_next)
        else:
            self.exited = True
            self.lock = False

        logger.debug('Page closed')

    def connect_signal(self, *args):
        handler_id = self.webkit_webview.connect(*args)
        self.cf_request_handlers_ids.append(handler_id)

    def disconnect_all_signals(self):
        for handler_id in self.cf_request_handlers_ids:
            self.webkit_webview.disconnect(handler_id)

        self.cf_request_handlers_ids = []

    def exit(self):
        if self.window.page != self.props.tag:
            # Page has already been popped or has never been pushed (no CF chanllenge)
            # No need to wait `hidden` event to flag it as exited
            self.exited = True
            return

        self.exited_auto = True
        self.window.navigationview.pop()

    def load_page(self, uri=None, cf_request=None, user_agent=None, auto_load_images=True):
        if self.lock or not self.exited:
            # Already in use or page exiting is not ended (pop animation not ended)
            return False

        self.exited = False
        self.exited_auto = False
        self.lock = True

        self.webkit_webview.get_settings().set_user_agent(user_agent or self.user_agent)
        self.webkit_webview.get_settings().set_auto_load_images(auto_load_images)

        self.cf_request = cf_request
        if self.cf_request:
            self.connect_signal('load-changed', self.cf_request.on_load_changed)
            self.connect_signal('load-failed', self.cf_request.on_load_failed)
            self.connect_signal('notify::title', self.cf_request.on_title_changed)
            uri = self.cf_request.url

        logger.debug('Load page %s', uri)

        GLib.idle_add(self.webkit_webview.load_uri, uri)

        return True

    def on_hidden(self, _page):
        self.exited = True

        if not self.exited_auto:
            # Webview has been left via a user interaction (back button, <ESC> key)
            self.cf_request.cancel()

        if self.cf_request and self.cf_request.error:
            # Cancel all pending CF requests with same URL if challenge was not completed
            for cf_request in self.cf_requests[:]:
                if cf_request.url == self.cf_request.url:
                    cf_request.cancel()
                    self.cf_requests.remove(cf_request)

        if not self.exited_auto:
            self.close_page()

    def pop_cf_request(self):
        if not self.cf_requests:
            return

        if self.load_page(cf_request=self.cf_requests[0]):
            self.cf_requests.pop(0)

    def push_cf_request(self, cf_request):
        self.cf_requests.append(cf_request)
        self.pop_cf_request()

    def show(self):
        self.window.navigationview.push(self)


class BypassCF:
    """Allows user to complete a server CF challenge using the Webview

    Several calls to this decorator can be concurrent. But only one will be honored at a time.
    """

    def __call__(self, func):
        self.func = func

        def wrapper(*args, **kwargs):
            bound_args = inspect.signature(self.func).bind(*args, **kwargs)
            args_dict = dict(bound_args.arguments)

            self.server = args_dict['self']
            self.url = self.server.bypass_cf_url or self.server.base_url

            if not self.server.has_cf:
                return self.func(*args, **kwargs)

            if self.server.session is None:
                # Try loading a previous session
                self.server.load_session()

            if self.server.session:
                logger.debug(f'{self.server.id}: Previous session found')
                # Locate CF cookie
                bypassed = False
                for cookie in self.server.session.cookies:
                    if cookie.name == 'cf_clearance':
                        # CF cookie is there
                        bypassed = True
                        break

                if bypassed:
                    logger.debug(f'{self.server.id}: Session has CF cookie. Checking...')
                    # Check session validity
                    r = self.server.session_get(self.url)
                    if r.ok:
                        logger.debug(f'{self.server.id}: Session OK')
                        return self.func(*args, **kwargs)

                    logger.debug(f'{self.server.id}: Session KO ({r.status_code})')
                else:
                    logger.debug(f'{self.server.id}: Session has no CF cookie. Loading page in webview...')

            self.cf_reload_count = 0
            self.done = False
            self.error = None
            self.load_event = None
            self.load_event_finished_timeout = 10
            self.load_events_monitor_id = None
            self.load_events_monitor_ts = None

            self.webview = Gio.Application.get_default().window.webview
            self.webview.push_cf_request(self)

            while not self.done and self.error is None:
                time.sleep(1)

            if self.error:
                logger.warning(self.error)
                raise CfBypassError()
            else:
                return self.func(*args, **kwargs)

        return wrapper

    def cancel(self):
        self.unmonitor_load_events()
        self.error = 'CF challenge bypass aborted'

    def monitor_challenge(self):
        # Detect CF challenge via JavaScript in current page
        # - No challenge found: change title to 'ready'
        # - A captcha is detected: change title to 'captcha 1' or 'captcha 2'
        # - An error occurs during challenge: change title to 'error'
        js = """
            let checkCF = setInterval(() => {
                if (document.getElementById('challenge-error-title')) {
                    // Your browser is outdated!
                    document.title = 'error';
                    clearInterval(checkCF);
                }
                else if (!document.querySelector('.ray-id')) {
                    document.title = 'ready';
                    clearInterval(checkCF);
                }
                else if (document.querySelector('input.pow-button')) {
                    // button
                    document.title = 'captcha 1';
                }
                else if (document.querySelector('iframe[id^="cf-chl-widget"]')) {
                    // checkbox in an iframe
                    document.title = 'captcha 2';
                }
            }, 100);
        """
        self.webview.webkit_webview.evaluate_javascript(js, -1)

    def monitor_load_events(self):
        # In case FINISHED event never appends
        # Page is considered to be loaded, if COMMITTED event has occurred, after load_event_finished_timeout seconds
        if self.load_event == WebKit.LoadEvent.COMMITTED and time.time() - self.load_events_monitor_ts > self.load_event_finished_timeout:
            logger.debug(f'Event FINISHED timeout ({self.load_event_finished_timeout}s)')
            self.monitor_challenge()
            self.load_events_monitor_id = None
            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE

    def on_load_changed(self, _webkit_webview, event):
        self.load_event = event
        logger.debug(f'Load changed: {event}')

        if event != WebKit.LoadEvent.REDIRECTED and '__cf_chl_tk' in self.webview.webkit_webview.get_uri():
            # Challenge has been passed
            # Disable images auto-load
            logger.debug('Disable images automatic loading')
            self.webview.webkit_webview.get_settings().set_auto_load_images(False)

        elif event == WebKit.LoadEvent.COMMITTED:
            # In case FINISHED event never appends
            self.unmonitor_load_events()
            logger.debug('Monitor load events')
            self.load_events_monitor_ts = time.time()
            self.load_events_monitor_id = GLib.idle_add(self.monitor_load_events)

        elif event == WebKit.LoadEvent.FINISHED:
            self.unmonitor_load_events()
            self.monitor_challenge()

    def on_load_failed(self, _webkit_webview, _event, uri, _gerror):
        self.error = f'CF challenge bypass failure: {uri}'

        self.unmonitor_load_events()
        self.webview.exit()
        self.webview.close_page()

    def on_title_changed(self, _webkit_webview, _title):
        title = self.webview.webkit_webview.props.title
        logger.debug(f'Title changed: {title}')

        if title == 'error':
            # CF error message detected
            # settings or a features related?
            self.error = 'CF challenge bypass error'
            self.webview.exit()
            self.webview.close_page()
            return

        if title.startswith('captcha'):
            self.cf_reload_count += 1
            if self.cf_reload_count > CF_RELOAD_MAX:
                self.error = 'Max CF reload exceeded'
                self.webview.exit()
                self.webview.close_page()
                return

            logger.debug(f'{self.server.id}: Captcha `{title}` detected, try #{self.cf_reload_count}')
            # Show webview, user must complete a CAPTCHA
            if self.webview.window.page != self.webview.props.tag:
                self.webview.title.set_title(_('Please complete CAPTCHA'))
                self.webview.title.set_subtitle(self.server.name)
                self.webview.show()

        if title != 'ready':
            return

        # Challenge has been passed
        # Exit from webview if end of challenge has not been detected in on_load_changed()
        # Webview should not be closed, we need to store cookies first
        self.webview.exit()

        logger.debug(f'{self.server.id}: Page loaded, getting cookies...')
        self.webview.network_session.get_cookie_manager().get_cookies(self.server.base_url, None, self.on_get_cookies_finished, None)

    def on_get_cookies_finished(self, cookie_manager, result, _user_data):
        self.server.session = requests.Session()
        self.server.session.headers.update({'User-Agent': self.webview.user_agent})

        # Copy libsoup cookies in session cookies jar
        for cookie in cookie_manager.get_cookies_finish(result):
            rcookie = requests.cookies.create_cookie(
                name=cookie.get_name(),
                value=cookie.get_value(),
                domain=cookie.get_domain(),
                path=cookie.get_path(),
                expires=cookie.get_expires().to_unix() if cookie.get_expires() else None,
                rest={'HttpOnly': cookie.get_http_only()},
                secure=cookie.get_secure(),
            )
            self.server.session.cookies.set_cookie(rcookie)

        logger.debug(f'{self.server.id}: Webview cookies successully copied in requests session')
        self.server.save_session()

        self.done = True
        self.webview.close_page()

    def unmonitor_load_events(self):
        if not self.load_events_monitor_id:
            return

        logger.debug('Unmonitor load events')
        try:
            GLib.source_remove(self.load_events_monitor_id)
        except Exception:
            pass
        finally:
            self.load_events_monitor_id = None


def eval_js(code):
    error = None
    res = None
    webview = Gio.Application.get_default().window.webview

    def load_page():
        if not webview.load_page(uri='about:blank'):
            return True

        webview.connect_signal('load-changed', on_load_changed)

        if DEBUG:
            webview.show()

    def on_evaluate_javascript_finish(_webkit_webview, result, _user_data=None):
        nonlocal error
        nonlocal res

        try:
            js_result = webview.webkit_webview.evaluate_javascript_finish(result)
        except GLib.GError:
            error = 'Failed to eval JS code'
        else:
            if js_result.is_string():
                res = js_result.to_string()

            if res is None:
                error = 'Failed to eval JS code'

        webview.close_page()

    def on_load_changed(_webkit_webview, event):
        if event != WebKit.LoadEvent.FINISHED:
            return

        webview.webkit_webview.evaluate_javascript(code, -1, None, None, None, on_evaluate_javascript_finish)

    GLib.timeout_add(100, load_page)

    while res is None and error is None:
        time.sleep(1)

    if error:
        logger.warning(error)
        raise requests.exceptions.RequestException()

    return res


def get_page_html(url, user_agent=None, wait_js_code=None, with_cookies=False):
    cookies = None
    error = None
    html = None
    webview = Gio.Application.get_default().window.webview

    def load_page():
        if not webview.load_page(uri=url, user_agent=user_agent, auto_load_images=False):
            return True

        webview.connect_signal('load-changed', on_load_changed)
        webview.connect_signal('load-failed', on_load_failed)
        webview.connect_signal('notify::title', on_title_changed)

        if DEBUG:
            webview.show()

    def on_get_cookies_finished(cookie_manager, result, _user_data):
        nonlocal cookies

        rcookies = []
        # Get libsoup cookies
        for cookie in cookie_manager.get_cookies_finish(result):
            rcookie = requests.cookies.create_cookie(
                name=cookie.get_name(),
                value=cookie.get_value(),
                domain=cookie.get_domain(),
                path=cookie.get_path(),
                expires=cookie.get_expires().to_unix() if cookie.get_expires() else None,
                rest={'HttpOnly': cookie.get_http_only()},
                secure=cookie.get_secure(),
            )
            rcookies.append(rcookie)

        cookies = rcookies

        webview.close_page()

    def on_get_html_finish(_webkit_webview, result, _user_data=None):
        nonlocal error
        nonlocal html

        js_result = webview.webkit_webview.evaluate_javascript_finish(result)
        if js_result:
            html = js_result.to_string()

        if html is not None:
            if with_cookies:
                logger.debug('Page loaded, getting cookies...')
                webview.network_session.get_cookie_manager().get_cookies(url, None, on_get_cookies_finished, None)
            else:
                webview.close_page()
        else:
            error = f'Failed to get chapter page html: {url}'
            webview.close_page()

    def on_load_changed(_webkit_webview, event):
        if event != WebKit.LoadEvent.FINISHED:
            return

        if wait_js_code:
            # Wait that everything needed has been loaded
            webview.webkit_webview.evaluate_javascript(wait_js_code, -1)
        else:
            webview.webkit_webview.evaluate_javascript('document.documentElement.outerHTML', -1, None, None, None, on_get_html_finish)

    def on_load_failed(_webkit_webview, _event, _uri, _gerror):
        nonlocal error

        error = f'Failed to load chapter page: {url}'

        webview.close_page()

    def on_title_changed(_webkit_webview, _title):
        nonlocal error

        if webview.webkit_webview.props.title == 'ready':
            # Everything we need has been loaded, we can retrieve page HTML
            webview.webkit_webview.evaluate_javascript('document.documentElement.outerHTML', -1, None, None, None, on_get_html_finish)

        elif webview.webkit_webview.props.title == 'abort':
            error = f'Failed to get chapter page html: {url}'
            webview.close_page()

    GLib.timeout_add(100, load_page)

    while (html is None or (with_cookies and cookies is None)) and error is None:
        time.sleep(1)

    if error:
        logger.warning(error)
        raise requests.exceptions.RequestException()

    return html if not with_cookies else (html, cookies)
