# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import datetime
from gettext import gettext as _
import gi
import logging
import sys
from threading import Timer

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Notify

from komikku.activity_indicator import ActivityIndicator
from komikku.card import CardPage
from komikku.categories_editor import CategoriesEditorPage
from komikku.debug_info import DebugInfo
from komikku.downloader import Downloader
from komikku.downloader import DownloadManagerPage
from komikku.explorer import Explorer
from komikku.history import HistoryPage
from komikku.library import LibraryPage
from komikku.models import backup_db
from komikku.models import init_db
from komikku.models import Settings
from komikku.models.database import clear_cached_data
from komikku.preferences import PreferencesDialog
from komikku.reader import ReaderPage
from komikku.servers.utils import get_allowed_servers_list
from komikku.support import SupportPage
from komikku.updater import Updater
from komikku.webview import WebviewPage

CREDITS = dict(
    artists=(
        'Tobias Bernard (bertob)',
    ),
    designers=(
        'Tobias Bernard (bertob)',
        'Valéry Febvre (valos)',
    ),
    developers=(
        'Mufeed Ali (fushinari)',
        'Gerben Droogers (Tijder)',
        'Valéry Febvre (valos)',
        'Aurélien Hamy (aunetx)',
        'Amelia Joison (amnetrine)',
        'David Keller (BlobCodes)',
        'Oleg Kiryazov (CakesTwix)',
        'Lili Kurek',
        'Liliana Prikler',
        'Romain Vaudois',
        'Arthur Williams (TAAPArthur)',
        'GrownNed',
        'ISO-morphism',
        'jaskaranSM',
    ),
    translators=(
        'abidin toumi (Arabic)',
        'Rayen Ghanmi (Arabic)',
        'Rafael Fontenelle (Brazilian Portuguese)',
        'Infinitive Witch (Brazilian Portuguese)',
        'Unidealistic Raccoon (Brazilian Portuguese)',
        'Roger VC (Catalan)',
        'Dingzhong Chen (Simplified Chinese)',
        'Eric-Song-Nop (Simplified Chinese)',
        'Inaha (Simplified Chinese)',
        'randint (Traditional Chinese)',
        'Zhao Se (Traditional Chinese)',
        'Heimen Stoffels (Dutch)',
        'Philip Goto (Dutch)',
        'Koen Benne (Dutch)',
        'Jiri Grönroos (Finnish)',
        'Irénée THIRION (French)',
        'Valéry Febvre (French)',
        'Mathieu B. (French)',
        'Sandor Odor (German)',
        'Liliana Prikler (German)',
        'gregorni (German)',
        'Liliana Marie Prikler (German)',
        'Alifiyan Rosyidi (Indonesian)',
        'Alim Satria (Indonesian)',
        'Mek101 (Italian)',
        'dedocc (Italian)',
        'Lili Kurek (Polish)',
        'ssantos (Portuguese)',
        'YXH (Romanian)',
        'shima (Russian)',
        'Valentin Chernetsov (Russian)',
        'FIONover (Russian)',
        'Анна Алешкина #нетвойне (Russian)',
        'Сергей (Russian)',
        'Óscar Fernández Díaz (Spanish)',
        'gallegonovato (Spanish)',
        'Ege Çelikçi (Turkish)',
        'Sabri Ünal (Turkish)',
        'Volkan Yıldırım (Turkish)',
        'CakesTwix (Ukrainian)',
    ),
    supporters=(
        'gondolyr',
        'José',
    ),
)


class Application(Adw.Application):
    application_id = None
    author = None
    profile = None
    version = None

    logger = None

    def __init__(self):
        super().__init__(application_id=self.application_id, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

        self.window = None

        self.set_resource_base_path('/info/febvre/Komikku')
        GLib.set_application_name('Komikku')

        logging.basicConfig(
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%d-%m-%y %H:%M:%S',
            level=logging.DEBUG if self.profile == 'development' else logging.INFO
        )
        self.logger = logging.getLogger('komikku')

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        if not self.window:
            self.window = ApplicationWindow(application=self, title='Komikku', icon_name=self.application_id)

        self.window.present()

    def do_command_line(self, command_line):
        self.do_activate()

        args = command_line.get_arguments()
        urls = args[1:]
        if not urls:
            return 0

        if len(urls) > 1:
            msg = _('Multiple URLs not supported')
            self.logger.warning(msg)
            self.window.show_notification(msg)

        url = urls[0]
        servers = []
        for data in get_allowed_servers_list(Settings.get_default()):
            server_class = getattr(data['module'], data['class_name'])
            if not server_class.base_url or not url.startswith(server_class.base_url):
                continue

            if initial_data := server_class.get_manga_initial_data_from_url(url):
                data['manga_initial_data'] = initial_data
                servers.append(data)

        if not servers:
            msg = _('Invalid URL {}, not handled by any server.').format(url)
            self.logger.info(msg)
            self.window.show_notification(msg)
        else:
            self.window.explorer.show(servers=servers)

        return 0

    def do_startup(self):
        Adw.Application.do_startup(self)

        init_db()
        Notify.init('Komikku')


@Gtk.Template.from_resource('/info/febvre/Komikku/ui/application_window.ui')
class ApplicationWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'

    network_available = False
    last_navigation_action = None

    overlay = Gtk.Template.Child('overlay')
    navigationview = Gtk.Template.Child('navigationview')
    breakpoint = Gtk.Template.Child('breakpoint')

    notification_timer = None
    notification_label = Gtk.Template.Child('notification_label')
    notification_revealer = Gtk.Template.Child('notification_revealer')
    pool_to_update_revealer = Gtk.Template.Child('pool_to_update_revealer')
    pool_to_update_spinner = Gtk.Template.Child('pool_to_update_spinner')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.application = kwargs['application']

        self._night_light_handler_id = 0
        self._night_light_proxy = None

        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/info/febvre/Komikku/ui/menu/main.xml')

        self.css_provider = Gtk.CssProvider.new()
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), self.css_provider, 400)

        self.activity_indicator = ActivityIndicator()
        self.overlay.add_overlay(self.activity_indicator)

        self.downloader = Downloader(self)
        self.updater = Updater(self)

        self.assemble_window()
        self.add_accelerators()
        self.add_actions()

        Gio.NetworkMonitor.get_default().connect('network-changed', self.on_network_status_changed)
        # Non-portal implementations of Gio.NetworkMonitor (app not running under Flatpak) don't actually change the value
        # unless the network state actually changes
        Gio.NetworkMonitor.get_default().emit('network-changed', None)

    @property
    def page(self):
        return self.navigationview.get_visible_page().props.tag

    @property
    def previous_page(self):
        previous_page = self.navigationview.get_previous_page(self.navigationview.get_visible_page())
        return previous_page.props.tag if previous_page else None

    @property
    def monitor(self):
        return self.get_display().get_monitor_at_surface(self.get_native().get_surface())

    def add_accelerators(self):
        self.application.set_accels_for_action('app.add', ['<Primary>plus'])
        self.application.set_accels_for_action('app.enter-search-mode', ['<Primary>f'])
        self.application.set_accels_for_action('app.fullscreen', ['F11'])
        self.application.set_accels_for_action('app.select-all', ['<Primary>a'])
        self.application.set_accels_for_action('app.preferences', ['<Primary>comma'])
        self.application.set_accels_for_action('app.shortcuts', ['<Primary>question'])
        self.application.set_accels_for_action('app.quit', ['<Primary>q', '<Primary>w'])

        self.reader.add_accelerators()

    def add_actions(self):
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about_menu_clicked)
        self.application.add_action(about_action)

        enter_search_mode_action = Gio.SimpleAction.new('enter-search-mode', None)
        enter_search_mode_action.connect('activate', self.enter_search_mode)
        self.application.add_action(enter_search_mode_action)

        fullscreen_action = Gio.SimpleAction.new('fullscreen', None)
        fullscreen_action.connect('activate', self.toggle_fullscreen)
        self.application.add_action(fullscreen_action)

        self.select_all_action = Gio.SimpleAction.new('select-all', None)
        self.select_all_action.connect('activate', self.select_all)
        self.application.add_action(self.select_all_action)

        preferences_action = Gio.SimpleAction.new('preferences', None)
        preferences_action.connect('activate', self.on_preferences_menu_clicked)
        self.application.add_action(preferences_action)

        shortcuts_action = Gio.SimpleAction.new('shortcuts', None)
        shortcuts_action.connect('activate', self.on_shortcuts_menu_clicked)
        self.application.add_action(shortcuts_action)

        support_action = Gio.SimpleAction.new('support', None)
        support_action.connect('activate', self.open_support)
        self.application.add_action(support_action)

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.quit)
        self.application.add_action(quit_action)

        self.explorer.search_page.add_actions()
        self.library.add_actions()
        self.card.add_actions()
        self.reader.add_actions()
        self.download_manager.add_actions()

    def assemble_window(self):
        # Restore window previous state (width/height and maximized) or use default
        self.set_default_size(*Settings.get_default().window_size)
        if Settings.get_default().window_maximized_state:
            self.maximize()

        self.set_size_request(360, 288)

        # Window
        self.connect('notify::default-width', self.on_resize)
        self.connect('notify::default-height', self.on_resize)
        self.connect('notify::fullscreened', self.on_resize)
        self.connect('notify::maximized', self.on_resize)
        self.connect('close-request', self.quit)

        self.navigationview.connect('popped', self.on_navigation_popped)
        self.navigationview.connect('pushed', self.on_navigation_pushed)

        self.controller_key = Gtk.EventControllerKey.new()
        self.controller_key.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.add_controller(self.controller_key)

        self.gesture_click = Gtk.GestureClick.new()
        self.gesture_click.set_button(0)
        self.gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.add_controller(self.gesture_click)

        # Init pages
        self.library = LibraryPage(self)
        self.card = CardPage(self)
        self.reader = ReaderPage(self)
        self.categories_editor = CategoriesEditorPage(self)
        self.download_manager = DownloadManagerPage(self)
        self.explorer = Explorer(self)
        self.history = HistoryPage(self)
        self.support = SupportPage(self)
        self.webview = WebviewPage(self)

        # Init dialogs
        self.preferences = PreferencesDialog(self)

        if self.application.profile in ('beta', 'development'):
            self.add_css_class('devel')

        # Theme (light or dark)
        self.init_theme()

        GLib.idle_add(self.library.populate)

    def confirm(self, title, message, confirm_label, confirm_callback, confirm_appearance=None, cancel_callback=None):
        def on_response(dialog, response_id):
            if response_id == 'yes':
                confirm_callback()
            elif response_id == 'cancel' and cancel_callback is not None:
                cancel_callback()

        dialog = Adw.AlertDialog.new(title)
        dialog.set_body(message)

        dialog.add_response('cancel', _('Cancel'))
        dialog.add_response('yes', confirm_label)

        dialog.set_close_response('cancel')
        dialog.set_default_response('cancel')
        if confirm_appearance is not None:
            dialog.set_response_appearance('yes', confirm_appearance)

        dialog.connect('response', on_response)
        dialog.present(self)

    def enter_search_mode(self, _action, _param):
        if self.page == 'library':
            self.library.toggle_search_mode()
        elif self.page == 'explorer.servers':
            self.explorer.servers_page.toggle_search_mode()
        elif self.page == 'history':
            self.history.toggle_search_mode()

    def hide_notification(self):
        self.notification_revealer.set_reveal_child(False)

    def init_theme(self):
        def set_color_scheme():
            if ((self._night_light_proxy.get_cached_property('NightLightActive') and Settings.get_default().night_light)
                    or Settings.get_default().color_scheme == 'dark'):
                color_scheme = Adw.ColorScheme.FORCE_DARK
            elif Settings.get_default().color_scheme == 'light':
                color_scheme = Adw.ColorScheme.FORCE_LIGHT
            else:
                color_scheme = Adw.ColorScheme.DEFAULT

            Adw.StyleManager.get_default().set_color_scheme(color_scheme)

        if not self._night_light_proxy:
            # Watch night light changes
            self._night_light_proxy = Gio.DBusProxy.new_sync(
                Gio.bus_get_sync(Gio.BusType.SESSION, None),
                Gio.DBusProxyFlags.NONE,
                None,
                'org.gnome.SettingsDaemon.Color',
                '/org/gnome/SettingsDaemon/Color',
                'org.gnome.SettingsDaemon.Color',
                None
            )

            def property_changed(_proxy, changed_properties, _invalidated_properties):
                properties = changed_properties.unpack()
                if 'NightLightActive' in properties:
                    set_color_scheme()

            self._night_light_handler_id = self._night_light_proxy.connect('g-properties-changed', property_changed)

        set_color_scheme()

    def on_about_menu_clicked(self, _action, _param):
        dialog = Adw.AboutDialog.new_from_appdata('/info/febvre/Komikku/appdata.xml', self.application.version)

        dialog.set_copyright(f'© 2019-{datetime.date.today().year} {self.application.author} et al.')
        dialog.set_comments(_("""A manga, manhwa, manhua, webtoons, webcomics and comics reader for GNOME

👉 Never forget, you can support the authors
by buying the official comics when they are
available in your region/language."""))
        dialog.set_artists(CREDITS['artists'])
        dialog.set_designers(CREDITS['designers'])
        dialog.set_developers(CREDITS['developers'])
        dialog.set_translator_credits('\n'.join(CREDITS['translators']))
        dialog.add_acknowledgement_section(_('Supporters'), CREDITS['supporters'])
        dialog.set_support_url('https://matrix.to/#/#komikku-gnome:matrix.org')
        dialog.add_link(_('Join Chat'), 'https://matrix.to/#/#komikku-gnome:matrix.org')

        # Override release notes
        dialog.set_release_notes("""
            <p>This version fixes a bug in Preferences. Switching NFSW content switches caused the application to crash.</p>

            <p>Changes in version 1.40.0</p>
            <ul>
                <li>[UX] Refined visuals taking advantage of the new capabilities of GNOME 46</li>
                <li>[Servers] Added Lelmanga (FR)</li>
                <li>[Servers] Added Lelscan (FR)</li>
                <li>[Servers] Added Night scans (EN)</li>
                <li>[Servers] Comic Book Plus (EN): Fixed search</li>
                <li>[Servers] MANGA Plus by SHUEISHA: Update</li>
                <li>[Servers] MangaDex: Added Tags filter</li>
                <li>[Servers] MangaLib (RU): Update</li>
                <li>[Servers] Mangaowl (EN): Update</li>
                <li>[Servers] Jpmangas (FR): Disabled</li>
                <li>[Servers] Reaper Scans (pt_BR): Disabled</li>
                <li>[Servers] Scan FR: Disabled</li>
                <li>[Servers] Scan Manga (FR): Disabled</li>
                <li>[L10n] Updated French, Russian, Spanish and Turkish translations</li>
            </ul>
            <p>Happy reading.</p>
        """)

        debug_info = DebugInfo(self.application)
        dialog.set_debug_info_filename('Komikku-debug-info.txt')
        dialog.set_debug_info(debug_info.generate())

        dialog.present(self)

    def on_navigation_popped(self, _nav, _page):
        self.last_navigation_action = 'pop'

        self.activity_indicator.stop()

    def on_navigation_pushed(self, _nav):
        self.last_navigation_action = 'push'

    def on_network_status_changed(self, monitor, _connected):
        connectivity = monitor.get_connectivity()
        if _connected != self.network_available:
            self.application.logger.warning('Connection status: {}'.format(connectivity))
        self.network_available = connectivity == Gio.NetworkConnectivity.FULL

        if self.network_available:
            # Automatically update library at startup
            if Settings.get_default().update_at_startup and not self.updater.update_at_startup_done:
                self.updater.update_library(startup=True)

            # Start Downloader
            if Settings.get_default().downloader_state:
                self.downloader.start()
        else:
            # Stop Updater
            self.updater.stop()

            # Stop Downloader
            if Settings.get_default().downloader_state:
                self.downloader.stop()

    def on_preferences_menu_clicked(self, _action, _param):
        self.preferences.show()

    def on_resize(self, _window, allocation):
        def on_maximized():
            # Gtk.Window::maximized (idem with Gdk.Toplevel:state) event is unreliable because it's emitted too earlier
            # We detect that maximization is effective by comparing monitor size and window size
            monitor_width = self.monitor.props.geometry.width / self.get_scale_factor()
            if self.get_width() < monitor_width and self.is_maximized():
                return True

            do_resize()

        def do_resize():
            self.library.on_resize()

        if allocation.name == 'maximized':
            GLib.idle_add(on_maximized)
        else:
            do_resize()

    def on_shortcuts_menu_clicked(self, _action, _param):
        builder = Gtk.Builder()
        builder.add_from_resource('/info/febvre/Komikku/ui/shortcuts_overview.ui')

        shortcuts_overview = builder.get_object('shortcuts_overview')
        shortcuts_overview.set_modal(True)
        shortcuts_overview.set_transient_for(self)
        shortcuts_overview.present()

    def open_support(self, _action, _param):
        self.support.show()

    def quit(self, *args, force=False):
        def confirm_callback():
            self.downloader.stop()
            self.updater.stop()

            GLib.idle_add(do_quit)

        def do_quit():
            if self.downloader.running or self.updater.running:
                return GLib.SOURCE_CONTINUE

            self.save_window_size()
            if Settings.get_default().clear_cached_data_on_app_close:
                clear_cached_data()

            backup_db()

            self.application.quit()

        if self.downloader.running or self.updater.running:
            message = [
                _('Are you sure you want to quit?'),
            ]
            if self.downloader.running:
                message.append(_('Some chapters are currently being downloaded.'))
            if self.updater.running:
                message.append(_('Some mangas are currently being updated.'))

            if not force:
                self.confirm(
                    _('Quit?'),
                    '\n'.join(message),
                    _('Quit'),
                    confirm_callback
                )
            else:
                confirm_callback()
        else:
            do_quit()

        return Gdk.EVENT_STOP

    def save_window_size(self):
        if self.is_fullscreen():
            return

        Settings.get_default().window_maximized_state = self.is_maximized()

        if not self.is_maximized():
            size = self.get_default_size()
            Settings.get_default().window_size = [size.width, size.height]

    def select_all(self, _action, _param):
        if self.page == 'library':
            self.library.select_all()
        elif self.page == 'card':
            self.card.chapters_list.select_all()
        elif self.page == 'download_manager':
            self.download_manager.select_all()

    def show_notification(self, message, timeout=5):
        # We use a custom in-app notification solution (Gtk.Revealer)
        # until Adw.ToastOverlay/Adw.Toast is fixed
        # see https://gitlab.gnome.org/GNOME/libadwaita/-/issues/440
        self.notification_revealer.set_margin_top(self.library.get_child().get_top_bar_height())

        self.notification_label.set_text(message)
        self.notification_revealer.set_reveal_child(True)

        if self.notification_timer:
            self.notification_timer.cancel()

        self.notification_timer = Timer(timeout, GLib.idle_add, args=[self.hide_notification])
        self.notification_timer.start()

    def toggle_fullscreen(self, _object, _gparam):
        if self.page != 'reader':
            return

        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()


if __name__ == '__main__':
    app = Application()
    app.run(sys.argv)
