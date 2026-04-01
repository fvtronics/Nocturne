# popout_window.py

from gi.repository import Gtk, Adw, GLib, Gst, Gio, GObject, Pango
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

    bottom_bar = Gtk.Template.Child()
    fs_title_el = Gtk.Template.Child()
    fs_progress_el = Gtk.Template.Child()
    fs_album_el = Gtk.Template.Child()
    fs_artist_el = Gtk.Template.Child()
    fs_timestamp_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    sidebar_stack = Gtk.Template.Child()

    def __init__(self, application, player, queue_list_el):
        super().__init__(
            application=application
        )

        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
        self.playing_page.last_song_id = current_song_id
        self.playing_page.pop_status_stack.set_visible_child_name("popin")

        GLib.idle_add(self.playing_page.setup, player)
        GLib.idle_add(self.lyrics_page.setup)
        GLib.idle_add(self.footer.setup)

        self.queue_page.replace_list_element(queue_list_el)
        self.playing_page.header_bar.get_ancestor(Adw.ToolbarView).set_extend_content_to_top_edge(False)
        self.playing_page.header_bar.set_show_start_title_buttons(True)
        self.playing_page.header_bar.set_show_end_title_buttons(True)

        self.footer.cover_el.set_size_request(100, 100)
        self.footer.cover_el.set_pixel_size(100)
        self.footer.title_el.set_wrap(True)
        self.footer.title_el.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.footer.title_el.set_lines(2)
        self.footer.title_el.get_ancestor(Gtk.Box).set_spacing(10)
        self.footer.progress_el.set_visible(False)
        self.footer_scale = Gtk.Scale(
            adjustment=Gtk.Adjustment(
                lower=0,
                upper=1,
                value=0
            ),
            css_classes=["p0"]
        )
        self.footer_scale.connect("change-value", self.playing_page.progress_bar_changed)
        self.footer.detail_container.append(self.footer_scale)
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.song_position_changed)
        integration.connect_to_model('currentSong', 'buttonState', self.state_stack_el.set_visible_child_name)

        fullscreen_btn = Gtk.Button(
            icon_name="view-fullscreen-symbolic",
            tooltip_text=_("Toggle Fullscreen")
        )
        fullscreen_btn.connect('clicked', self.toggle_fullscreen)
        self.playing_page.header_bar.pack_start(fullscreen_btn)

    @Gtk.Template.Callback()
    def close_request(self, window):
        self.get_root().activate_action("app.close_popout_window")

    @Gtk.Template.Callback()
    def fullscreen_toggled(self, window, gparam):
        isFullscreen = window.is_fullscreen()
        self.split_view.set_max_sidebar_width(1080 if isFullscreen else 320)
        self.bottom_bar.set_visible(isFullscreen)
        self.toolbarview.set_extend_content_to_top_edge(isFullscreen)
        self.sidebar_stack.set_visible_child_name('view' if isFullscreen else 'controller')
        self.header_view_switcher.set_visible(not isFullscreen)

    def song_position_changed(self, positionSeconds:int):
        integration = get_current_integration()
        songId = integration.loaded_models.get('currentSong').get_property('songId')
        if model := integration.loaded_models.get(songId):
            duration = model.get_property('duration')
            self.fs_timestamp_el.set_label('-{}'.format(get_display_time(duration - positionSeconds)))
        self.footer_scale.set_value(positionSeconds)
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
            self.footer_scale.get_adjustment().set_upper(model.get_property('duration'))
            self.fs_progress_el.get_adjustment().set_upper(model.get_property('duration'))
            self.set_title(model.get_property('title'))
            self.fs_title_el.set_label(model.get_property('title'))
            self.fs_album_el.set_label(model.get_property('album'))
            self.fs_artist_el.set_label(model.get_property('artists')[0].get('name') if len(model.get_property('artists')) > 0 else model.get_property('artist'))
            self.cover_el.set_paintable(model.get_property('gdkPaintable'))

    @Gtk.Template.Callback()
    def progress_bar_changed(self, scale_el, scroll_type, value):
        self.playing_page.progress_bar_changed(scale_el, scroll_type, value)

