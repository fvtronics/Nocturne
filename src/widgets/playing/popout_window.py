# popout_window.py

from gi.repository import Gtk, Adw, GLib, Gst, Gio, GObject, Pango, Gdk
from . import PlayingControlPage
from ...integrations import get_current_integration
from ...constants import get_display_time

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/popout_window.ui')
class PopoutWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NocturnePopoutWindow'

    toolbarview = Gtk.Template.Child()
    header_view_switcher = Gtk.Template.Child()
    breakpoint_el = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    playing_page = Gtk.Template.Child()
    lyrics_page = Gtk.Template.Child()
    queue_page = Gtk.Template.Child()
    footer = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    footer_spectrum_el = Gtk.Template.Child()

    bottom_bar = Gtk.Template.Child()
    fs_spectrum_el = Gtk.Template.Child()
    fs_title_el = Gtk.Template.Child()
    fs_progress_el = Gtk.Template.Child()
    fs_album_el = Gtk.Template.Child()
    fs_artist_el = Gtk.Template.Child()
    fs_timestamp_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    sidebar_stack = Gtk.Template.Child()
    toggle_fullscreen_el = Gtk.Template.Child()

    def __init__(self, application, fullscreened):
        super().__init__(
            application=application,
            fullscreened=fullscreened
        )

        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
        self.playing_page.last_song_id = current_song_id
        self.playing_page.pop_status_stack.set_visible_child_name("popin")

        GLib.idle_add(self.playing_page.setup)
        GLib.idle_add(self.lyrics_page.setup)
        GLib.idle_add(self.footer.setup)
        GLib.idle_add(self.queue_page.setup)

        self.playing_page.header_bar.get_ancestor(Adw.ToolbarView).set_extend_content_to_top_edge(False)
        self.playing_page.header_bar.set_show_start_title_buttons(True)
        self.playing_page.header_bar.set_show_end_title_buttons(True)

        self.footer.set_property('forceHugeMode', True)
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.song_position_changed)
        integration.connect_to_model('currentSong', 'buttonState', self.state_stack_el.set_visible_child_name)

        fullscreen_btn = Gtk.Button(
            icon_name="view-fullscreen-symbolic",
            tooltip_text=_("Toggle Fullscreen")
        )
        fullscreen_btn.connect('clicked', self.toggle_fullscreen)
        self.playing_page.header_bar.pack_start(fullscreen_btn)
        self.footer_spectrum_el.setup()
        self.fs_spectrum_el.setup()

        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")

        self.settings.connect('changed::popout-dynamic-bg-mode', self.dynamic_bg_mode_changed)
        self.dynamic_bg_mode_changed(self.settings, 'popout-dynamic-bg-mode')
        self.settings.connect('changed::use-dynamic-accent', self.css_toggled, 'dynamic-accent')
        self.css_toggled(self.settings, 'use-dynamic-accent', 'dynamic-accent')

    def css_toggled(self, settings, key, css_class):
        if settings.get_value(key).unpack():
            self.add_css_class(css_class)
        else:
            self.remove_css_class(css_class)

    def dynamic_bg_mode_changed(self, settings, key):
        value = settings.get_value(key).unpack()
        self.remove_css_class('dynamic-bg-gradient')
        self.remove_css_class('dynamic-bg-blur')
        if value:
            self.add_css_class('dynamic-bg-{}'.format(value))

    @Gtk.Template.Callback()
    def close_request(self, window):
        self.get_root().activate_action("app.close_popout_window")

    def song_position_changed(self, positionSeconds:int):
        integration = get_current_integration()
        songId = integration.loaded_models.get('currentSong').get_property('songId')
        if model := integration.loaded_models.get(songId):
            duration = model.get_property('duration')
            self.fs_timestamp_el.set_label('-{}'.format(get_display_time(duration - positionSeconds)))
        self.fs_progress_el.set_value(positionSeconds)

    @Gtk.Template.Callback()
    def toggle_fullscreen(self, button):
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

    def song_changed(self, id:str):
        integration = get_current_integration()
        if model := integration.loaded_models.get(id):
            self.fs_progress_el.get_adjustment().set_upper(model.get_property('duration'))
            self.set_title(model.get_property('title'))
            self.fs_title_el.set_label(model.get_property('title'))
            self.fs_album_el.get_child().set_label(model.get_property('album'))
            self.fs_album_el.set_tooltip_text(model.get_property('album'))
            self.fs_album_el.set_action_target_value(GLib.Variant.new_string(model.get_property('albumId')))
            self.fs_album_el.set_action_name("app.show_album")
            artist = model.get_property('artists')[0] if len(model.get_property('artists')) > 0 else {'name': model.get_property('artist'), 'id': model.get_property('artistId')}
            self.fs_artist_el.get_child().set_label(artist.get('name'))
            self.fs_artist_el.set_tooltip_text(artist.get('name'))
            self.fs_artist_el.set_action_target_value(GLib.Variant.new_string(artist.get('id')))
            self.fs_artist_el.set_action_name("app.show_artist")

            # Paintable
            paintable = model.get_property('gdkPaintable')
            if paintable:
                self.cover_el.remove_css_class('p50')
            else:
                icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
                paintable = icon_theme.lookup_icon(
                    'music-note-symbolic',
                    None,
                    64,
                    1,
                    Gtk.TextDirection.NONE,
                    0
                )
                self.cover_el.add_css_class('p50')
            GLib.idle_add(self.cover_el.set_paintable, paintable)

            # Radio
            self.fs_artist_el.set_visible(not model.get_property('isRadio'))
            self.fs_album_el.set_visible(not model.get_property('isRadio'))
            self.fs_timestamp_el.set_visible(not model.get_property('isRadio'))
            self.fs_progress_el.set_visible(not model.get_property('isRadio'))

    @Gtk.Template.Callback()
    def progress_bar_changed(self, scale_el, scroll_type, value):
        self.playing_page.progress_bar_changed(scale_el, scroll_type, value)

    @Gtk.Template.Callback()
    def big_mode_apply(self, breakpoint_el):
        self.add_css_class('big-mode')

    @Gtk.Template.Callback()
    def big_mode_unapply(self, breakpoint_el):
        self.remove_css_class('big-mode')

    @Gtk.Template.Callback()
    def fullscreen_toggled(self, window, gparam):
        self.toggle_fullscreen_el.set_icon_name('view-unfullscreen-symbolic' if window.is_fullscreen() else 'view-fullscreen-symbolic')
