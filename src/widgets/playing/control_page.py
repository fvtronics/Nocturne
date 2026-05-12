# control_page.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject, Gst, Gio
from ...integrations import get_current_integration
from ...constants import MPRIS_COVER_PATH, get_display_time
import threading, random, io, os, glob
from urllib.parse import urlparse
from .player import Player

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/control_page.ui')
class PlayingControlPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlayingControlPage'

    header_bar = Gtk.Template.Child()
    spectrum_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    radio_homepage_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    album_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    positive_progress_el = Gtk.Template.Child()
    negative_progress_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    show_sidebar_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    rating_container = Gtk.Template.Child()

    # Used to disconnect star_el when song changes
    # song_id, connection_id
    starred_connection = [None, None]

    def setup(self):
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'positionSeconds', self.update_position)
        integration.connect_to_model('currentSong', 'buttonState', self.state_stack_el.set_visible_child_name)
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'displaySongTitle', self.display_title_changed)
        integration.connect_to_model('currentSong', 'displaySongArtist', self.display_artist_changed)
        self.spectrum_el.setup()
        self.setup_sidebar_button_connection()
        if stack := self.get_ancestor(Gtk.Stack):
            GLib.idle_add(stack.get_parent().set_overflow, Gtk.Overflow.HIDDEN)
            if stack2 := stack.get_parent().get_parent():
                GLib.idle_add(stack2.get_parent().set_overflow, Gtk.Overflow.HIDDEN)

    def update_position(self, positionSeconds:int):
        integration = get_current_integration()
        current_song = integration.loaded_models.get('currentSong')
        if current_song:
            song = integration.loaded_models.get(current_song.get_property('songId'))
            if song:
                label_positive = get_display_time(positionSeconds)
                label_negative = get_display_time(song.get_property('duration') - positionSeconds)
                self.positive_progress_el.set_label(label_positive)
                self.negative_progress_el.set_label('-{}'.format(label_negative))
                if not integration.loaded_models.get('currentSong').get_property('seeking'):
                    self.progress_el.get_adjustment().set_value(positionSeconds)

    def breakpoint_toggled(self, active:bool):
        self.show_sidebar_el.set_visible(active)
        if isinstance(self.get_parent(), Adw.NavigationView) and not self.get_parent().get_vhomogeneous():
            self.get_parent().set_vhomogeneous(True)

    def setup_sidebar_button_connection(self):
        self.get_root().breakpoint_el.connect('apply', lambda *_: self.breakpoint_toggled(True))
        self.get_root().breakpoint_el.connect('unapply', lambda *_: self.breakpoint_toggled(False))
        is_small = self.get_root().get_width() < 480
        self.breakpoint_toggled(is_small and self.get_root().get_width() > 0)

    @Gtk.Template.Callback()
    def progress_bar_changed(self, scale_el, scroll_type, value):
        value = scale_el.get_adjustment().get_value()
        integration = get_current_integration()
        integration.loaded_models.get('currentSong').set_property('seeking', True)
        def change_time(val):
            integration.loaded_models.get('currentSong').set_property('seeking', False)
            nanoseconds = int(val * Gst.SECOND)
            self.get_root().get_application().player.gst.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanoseconds
            )
        GLib.timeout_add(500, lambda v=value: change_time(v) if v == scale_el.get_adjustment().get_value() else None)

    @Gtk.Template.Callback()
    def show_content_clicked(self, button):
        view = self.get_ancestor(Adw.NavigationSplitView)
        if view:
            view.set_show_content(True)

    @Gtk.Template.Callback()
    def change_rating(self, button):
        integration = get_current_integration()
        songId = integration.loaded_models.get('currentSong').get_property('songId')
        try:
            rating = int(button.get_name())
            if rating == integration.loaded_models.get(songId).get_property('userRating'):
                rating = 0
        except:
            return

        if integration.setRating(songId, rating):
            for i, el in enumerate(list(self.rating_container)):
                el.set_icon_name("starred-symbolic" if rating >= i+1 else "non-starred-symbolic")

    def change_bottom_sheet_state(self, playing:bool):
        bottom_sheet = self.get_ancestor(Adw.BottomSheet)
        if bottom_sheet:
            bottom_sheet.set_can_open(playing)
            if not playing:
                bottom_sheet.set_open(False)
            bottom_sheet.set_reveal_bottom_bar(playing)

        if root := self.get_root():
            if application := root.get_application():
                if playing:
                    application.inhibit_suspend()
                else:
                    application.uninhibit_suspend()
                    if popout_window := application.popout_window:
                        popout_window.close()

    def update_interface(self, model):
        if not model:
            return

        integration = get_current_integration()

        # HomePage (radio)
        if model.get_property('isRadio') and model.get_property('streamUrl'):
            stream_url = urlparse(model.get_property('streamUrl'))
            homepage_url = '{}://{}'.format(stream_url.scheme, stream_url.netloc)
            self.radio_homepage_el.set_tooltip_text(homepage_url)
            self.radio_homepage_el.set_action_target_value(GLib.Variant.new_string(homepage_url))
        self.radio_homepage_el.set_visible(model.get_property('isRadio') and model.get_property('streamUrl'))

        # Timestamp (radio)
        self.positive_progress_el.set_visible(not model.get_property('isRadio'))
        self.negative_progress_el.set_visible(not model.get_property('isRadio'))

        # Artist
        artists = model.get_property('artists')
        if len(artists) > 0:
            self.artist_el.set_visible(True)
            self.artist_el.set_action_target_value(GLib.Variant.new_string(artists[0].get('id')))
            self.artist_el.set_action_name("app.show_artist")
            self.artist_el.get_child().set_label(artists[0].get('name'))
            self.artist_el.set_tooltip_text(artists[0].get('name'))
        else:
            self.artist_el.set_visible(False)

        # Album
        self.album_el.get_child().set_label(model.get_property('album'))
        self.album_el.set_tooltip_text(model.get_property('album'))
        self.album_el.set_action_target_value(GLib.Variant.new_string(model.get_property('albumId')))
        self.album_el.set_action_name("app.show_album")
        self.album_el.set_visible(self.album_el.get_child().get_label())

        # External File
        self.album_el.get_ancestor(Adw.WrapBox).set_sensitive(not model.get_property('isExternalFile'))

        # Progressbar
        self.progress_el.get_adjustment().set_upper(model.get_property('duration'))
        self.progress_el.set_visible(not model.get_property('isRadio'))

        # Rating
        rating = model.get_property("userRating")
        for i, el in enumerate(list(self.rating_container)):
            el.set_icon_name("starred-symbolic" if rating >= i+1 else "non-starred-symbolic")
        self.rating_container.set_visible(not model.get_property('isRadio'))

        # Star
        self.star_el.set_visible(not model.get_property('isRadio') and not model.get_property('isExternalFile'))

        # Star Connection
        if self.starred_connection[0] and self.starred_connection[1]:
            integration.loaded_models.get(self.starred_connection[0]).disconnect(self.starred_connection[1])

        self.starred_connection[0] = model.get_property('id')
        self.starred_connection[1] = integration.connect_to_model(self.starred_connection[0], 'starred', self.update_starred)
        self.star_el.set_action_target_value(GLib.Variant.new_string(self.starred_connection[0]))

    def display_title_changed(self, display_title:str):
        self.title_el.set_label(display_title)
        self.title_el.set_tooltip_text(display_title)

    def display_artist_changed(self, display_artist:str):
        self.radio_homepage_el.get_child().set_label(display_artist)

    def song_changed(self, song_id:str):
        integration = get_current_integration()
        model = integration.loaded_models.get(song_id)
        self.update_interface(model)
        threading.Thread(target=self.update_cover_art, daemon=True).start()

    def update_cover_art(self):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').get_property('songId')
        if model := integration.loaded_models.get(song_id):
            mpris_path = os.path.join(MPRIS_COVER_PATH, "{}.png".format(song_id))
            for old_file in glob.glob(f"{MPRIS_COVER_PATH}/*.png"):
                os.remove(old_file)
            if paintable := integration.getCoverArt(song_id, big=True):
                GLib.idle_add(self.cover_el.set_paintable, paintable)
                GLib.idle_add(self.cover_el.set_visible, True)
                paintable.save_to_png(mpris_path)
            else:
                GLib.idle_add(self.cover_el.set_paintable, None)
                GLib.idle_add(self.cover_el.set_visible, False)

    def update_starred(self, starred:bool):
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.remove_css_class('dim-label')
            self.star_el.set_icon_name('heart-filled-symbolic')
            self.star_el.set_tooltip_text(_('Favorite'))
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.add_css_class('dim-label')
            self.star_el.set_icon_name('heart-outline-thick-symbolic')
            self.star_el.set_tooltip_text(_('Not Favorite'))

