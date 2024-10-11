# Copyright (C) 2019-2024 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
from queue import Empty
from queue import Queue
import threading
import time

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import Gtk

from komikku.servers import DOWNLOAD_MAX_DELAY
from komikku.utils import CoverPicture
from komikku.utils import html_escape
from komikku.utils import MISSING_IMG_RESOURCE_PATH

THUMB_WIDTH = 41
THUMB_HEIGHT = 58


@Gtk.Template.from_resource('/info/febvre/Komikku/ui/card_tracking.ui')
class TrackingDialog(Adw.PreferencesDialog):
    __gtype_name__ = 'TrackingDialog'

    group = Gtk.Template.Child('group')
    selected_tracker_row = None
    tracker_rows = []

    def __init__(self, window):
        super().__init__()

        self.window = window

        for _id, tracker in self.window.trackers.trackers.items():
            row = TrackerRow(window, tracker)
            self.group.add(row)
            self.tracker_rows.append(row)

        self.search_subpage = TrackingSearchSubPage(self.window)
        self.search_subpage.connect('hiding', self.on_search_subpage_hiding)

        self.connect('closed', self.on_closed)

    def add_tracking(self, id):
        def run():
            manga = self.window.card.manga
            if manga.tracking is None:
                manga.tracking = {}

            tracker = self.selected_tracker_row.tracker
            data = tracker.get_manga_data(id)
            data['_synced'] = True

            manga.tracking[tracker.id] = data

            manga.update({'tracking': manga.tracking})

            GLib.idle_add(complete, data)

        def complete(data):
            self.pop_subpage()
            self.selected_tracker_row.init(data)

        self.selected_tracker_row.set_arrow_visible(True)
        self.selected_tracker_row.btn.set_visible(False)

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_closed(self, _dialog):
        self.window.trackers.sync()

    def on_search_subpage_hiding(self, _page):
        self.search_subpage.thread_covers_stop_flag = True
        self.resize()

    def resize(self):
        self.set_content_height(-1)

    def show(self):
        count = 0
        for tracker_row in self.tracker_rows:
            if tracker_row.init():
                count += 1

        if count == 0:
            self.window.add_notification(_('No tracking services available'))
            return

        self.present(self.window)

    def show_search(self, tracker):
        self.search_subpage.init(tracker, self.window.card.manga.name)
        self.push_subpage(self.search_subpage)
        self.resize()


class TracherResultRow(Adw.ActionRow):
    def __init__(self, window, data):
        self.window = window
        self.data = data

        super().__init__(title=html_escape(data['name']), use_markup=True)

        subtitle = []
        if data.get('authors'):
            subtitle.append(html_escape(data['authors']))
        if data.get('start_date'):
            subtitle.append(data['start_date'])
        subtitle.append(data['status'])
        self.set_subtitle(' - '.join(subtitle))

        self.btn = Gtk.Button(valign=Gtk.Align.CENTER)
        self.btn.set_label(_('Track'))
        self.btn.connect('clicked', lambda _btn: self.window.card.tracking_dialog.add_tracking(data['id']))
        self.add_suffix(self.btn)

    def set_cover(self, data):
        picture = CoverPicture.new_from_data(data, THUMB_WIDTH, THUMB_HEIGHT, True) if data else None
        if picture is None:
            picture = CoverPicture.new_from_resource(MISSING_IMG_RESOURCE_PATH, THUMB_WIDTH, THUMB_HEIGHT)
        else:
            self.cover_data = data

        self.add_prefix(picture)


class TrackerRow(Adw.ExpanderRow):
    def __init__(self, window, tracker):
        self.window = window
        self.tracker = tracker

        super().__init__(title=self.tracker.name)

        logo = Gtk.Picture.new_for_filename(self.tracker.logo_path)
        logo.props.margin_top = 9
        logo.props.margin_bottom = 9
        self.add_prefix(logo)

        self.set_arrow_visible(False)

        self.btn = Gtk.Button(valign=Gtk.Align.CENTER)
        self.btn.set_label(_('Use'))
        self.btn.connect('clicked', self.on_btn_clicked)
        self.add_suffix(self.btn)

        # Action (tracker page, delete)
        self.action_row = Adw.ActionRow()
        cancel_button = Gtk.Button.new_from_icon_name('user-trash-symbolic')
        cancel_button.props.valign = Gtk.Align.CENTER
        cancel_button.set_tooltip_text(_('Cancel Tracking'))
        cancel_button.connect('clicked', self.cancel_tracking)
        self.action_row.add_suffix(cancel_button)
        self.add_row(self.action_row)

        # Status
        self.status_row = Adw.ComboRow(title=_('Status'))
        statuses = Gtk.StringList()
        for _status, internal_status in self.tracker.STATUSES_MAPPING.items():
            statuses.append(_(self.tracker.INTERNAL_STATUSES[internal_status]))
        self.status_row.set_model(statuses)
        self.status_changed_handler_id = self.status_row.connect('notify::selected', self.update_tracking_data)
        self.add_row(self.status_row)

        # Score
        self.score_row = Adw.SpinRow(title=_('Score'), wrap=True)
        self.score_changed_handler_id = self.score_row.connect('notify::value', self.update_tracking_data)
        self.add_row(self.score_row)

        # Chapters progress
        self.chapters_progress_row = Adw.SpinRow(title=_('Chapter'), wrap=True)
        self.num_chapter_changed_handler_id = self.chapters_progress_row.connect('notify::value', self.update_tracking_data)
        self.add_row(self.chapters_progress_row)

    def cancel_tracking(self, _btn):
        def confirm_callback():
            manga = self.window.card.manga
            manga.tracking.pop(self.tracker.id)
            manga.update({'tracking': manga.tracking})
            self.init()

        self.window.confirm(
            _('Delete?'),
            _('Are you sure you want to cancel tracking?'),
            _('Delete'),
            confirm_callback,
            confirm_appearance=Adw.ResponseAppearance.DESTRUCTIVE
        )

    def init(self, data=None):
        def run():
            try:
                id = self.window.card.manga.tracking[self.tracker.id]['id']
                data = self.tracker.get_manga_data(id)
            except Exception:
                data = self.window.card.manga.tracking[self.tracker.id]

            GLib.idle_add(complete, data)

        def complete(data):
            self.set_enable_expansion(True)
            self.set_expanded(True)
            self.set_arrow_visible(True)
            self.btn.set_visible(False)
            self.action_row.set_title(f'<a href="{self.tracker.get_manga_url(data['id'])}">{html_escape(data["name"])}</a>')

            with self.chapters_progress_row.handler_block(self.num_chapter_changed_handler_id):
                adj = Gtk.Adjustment(
                    value=data['chapters_progress'] or 0,
                    lower=0,
                    upper=data['chapters'] or 10000,
                    step_increment=1,
                    page_increment=10
                )
                self.chapters_progress_row.set_adjustment(adj)

            with self.score_row.handler_block(self.score_changed_handler_id):
                self.score_row.format = self.tracker.get_user_score_format(data['score_format'])
                adj = Gtk.Adjustment(
                    value=data['score'] or 0,
                    lower=self.score_row.format['min'],
                    upper=self.score_row.format['max'],
                    step_increment=self.score_row.format['step'],
                )
                self.score_row.configure(adj, 0, self.score_row.format['step'] * 10 if self.score_row.format['step'] != 1 else 0)

            with self.status_row.handler_block(self.status_changed_handler_id):
                self.status_row.set_selected(self.tracker.get_status_index(data['status']))

        def reset():
            self.set_expanded(False)
            self.set_enable_expansion(False)
            self.set_arrow_visible(False)
            self.btn.set_visible(True)
            self.action_row.set_title('')

        # Is the tracker connected and active?
        tracker_data = self.tracker.get_data()
        active = tracker_data and tracker_data['active']
        self.set_visible(active)

        if data is None:
            if self.window.card.manga.tracking and self.window.card.manga.tracking.get(self.tracker.id):
                thread = threading.Thread(target=run)
                thread.daemon = True
                thread.start()
            else:
                self.set_expanded(False)
                self.set_enable_expansion(False)
                self.set_arrow_visible(False)
                self.btn.set_visible(True)
                self.action_row.set_title('')
        else:
            complete(data)

        return active

    def on_btn_clicked(self, _btn):
        self.window.card.tracking_dialog.show_search(self.tracker)
        self.window.card.tracking_dialog.selected_tracker_row = self

    def set_arrow_visible(self, visible):
        action_row = self.get_first_child().get_first_child().get_first_child()
        arrow_img = action_row.get_first_child().get_last_child().get_last_child()
        arrow_img.set_visible(visible)

    def update_tracking_data(self, _row, _gparam):
        print('UPDATE', self.tracker.id)
        data = {
            'chapters_progress': self.chapters_progress_row.get_value(),
            'score': self.score_row.get_value() * self.score_row.format['raw_factor'],  # RAW
            'status': self.tracker.get_status_from_index(self.status_row.get_selected()),
            '_synced': False,
        }

        manga = self.window.card.manga
        manga.tracking[self.tracker.id].update(data)
        manga.update({'tracking': manga.tracking})


@Gtk.Template.from_resource('/info/febvre/Komikku/ui/card_tracking_search.ui')
class TrackingSearchSubPage(Adw.NavigationPage):
    __gtype_name__ = 'TrackingSearchSubPage'

    searchentry = Gtk.Template.Child('searchentry')
    group = Gtk.Template.Child('group')

    def __init__(self, window):
        super().__init__()

        self.window = window
        self.queue = Queue()
        self.thread_covers = None
        self.thread_covers_stop_flag = False

        self.tracker = None

        self.searchentry.connect('activate', lambda _w: self.search())

    def clear(self):
        # Empty queue
        while not self.queue.empty():
            try:
                self.queue.get()
                self.queue.task_done()
            except Empty:
                continue

        # Empty group
        listbox = self.group.get_first_child().get_last_child().get_first_child()
        row = listbox.get_first_child()
        while row:
            next_row = row.get_next_sibling()

            self.group.remove(row)
            row = next_row

    def init(self, tracker, name=None):
        self.tracker = tracker

        self.searchentry.set_placeholder_text(_('Search {}').format(self.tracker.name))
        self.searchentry.set_text(name)

        self.search()

    def render_covers(self):
        """
        Fetch and display covers of result rows

        This method is interrupted when the navigation page is left.
        """
        def run():
            while not self.queue.empty() and self.thread_covers_stop_flag is False:
                try:
                    row = self.queue.get()
                except Empty:
                    continue
                else:
                    try:
                        data, _etag, rtime = self.tracker.get_manga_cover_image(row.data['cover'])
                    except Exception:
                        pass
                    else:
                        GLib.idle_add(row.set_cover, data)

                        if rtime:
                            time.sleep(min(2 * rtime, DOWNLOAD_MAX_DELAY))

                    self.queue.task_done()

        self.thread_covers_stop_flag = False
        self.thread_covers = threading.Thread(target=run)
        self.thread_covers.daemon = True
        self.thread_covers.start()

    def search(self):
        self.clear()

        term = self.searchentry.get_text().strip()
        results = self.tracker.search(term)

        if results:
            for result in results:
                row = TracherResultRow(self.window, result)
                self.group.add(row)
                self.queue.put(row)

            self.render_covers()
