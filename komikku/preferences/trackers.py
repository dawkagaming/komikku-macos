# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import Gtk

from komikku.consts import LOGO_SIZE


class TrackerRow(Adw.ActionRow):
    def __init__(self, window, tracker):
        self.window = window
        self.tracker = tracker

        super().__init__(title=self.tracker.name, activatable=False)

        if self.tracker.logo_path:
            logo = Gtk.Image()
            logo.set_pixel_size(LOGO_SIZE)
            logo.set_from_file(self.tracker.logo_path)
        else:
            logo = Adw.Avatar.new(LOGO_SIZE, self.tracker.name, True)

        self.add_prefix(logo)

        self.btn = Gtk.Button(valign=Gtk.Align.CENTER)

        granted, access_token_valid = self.tracker.is_granted()
        if granted and access_token_valid:
            self.active = True
            self.btn.set_label(_('Disconnect'))
            self.btn.set_css_classes(['destructive-action'])
        else:
            self.active = False

            if granted and not access_token_valid:
                self.set_subtitle(_('Connection is expired'))
                self.btn.set_label(_('Reconnect'))
                self.btn.set_css_classes(['suggested-action'])
            else:
                self.btn.set_label(_('Connect'))
                self.btn.set_css_classes([])

        self.btn.connect('clicked', self.on_btn_clicked)
        self.add_suffix(self.btn)

    def on_btn_clicked(self, _btn):
        group = None

        def open_dialog():
            nonlocal group

            group = Adw.PreferencesGroup()

            username_entry = Adw.EntryRow(title=_('Username'))
            username_entry.add_prefix(Gtk.Image.new_from_icon_name('avatar-default-symbolic'))
            group.add(username_entry)

            password_entry = Adw.PasswordEntryRow(title=_('Password'))
            password_entry.add_prefix(Gtk.Image.new_from_icon_name('dialog-password-symbolic'))
            group.add(password_entry)

            self.window.open_dialog(
                self.tracker.name,
                child=group,
                confirm_label=_('Connect'),
                confirm_callback=connect_dialog
            )

        def connect_dialog():
            username_entry = group.get_row(0)
            password_entry = group.get_row(1)
            success, error = self.tracker.request_access_token(username_entry.get_text(), password_entry.get_text())
            GLib.idle_add(connect_finish, success, error)

        def connect_webview():
            success, error = self.tracker.request_access_token()
            GLib.idle_add(connect_finish, success, error)

        def connect_finish(success, error):
            if success:
                self.active = True
                self.btn.set_label(_('Disconnect'))
                self.btn.set_css_classes(['destructive-action'])

            elif error == 'load_failed':
                self.window.preferences.add_toast(Adw.Toast.new(_('Failed to request client access')))

            elif error == 'locked':
                self.window.preferences.add_toast(Adw.Toast.new(_('Webview is currently in used. Please retry later.')))

            elif error == 'canceled':
                self.window.preferences.add_toast(Adw.Toast.new(error))

        def disconnect():
            self.tracker.data = None

            self.active = False
            self.btn.set_label(_('Connect'))
            self.btn.set_css_classes([])

        if not self.active:
            if self.tracker.authorize_url:
                thread = threading.Thread(target=connect_webview)
                thread.daemon = True
                thread.start()
            else:
                open_dialog()

        else:
            self.window.open_dialog(
                _('Disconnect from {}').format(self.tracker.name),
                confirm_label=_('Disconnect'),
                confirm_callback=disconnect,
                confirm_appearance=Adw.ResponseAppearance.DESTRUCTIVE
            )
