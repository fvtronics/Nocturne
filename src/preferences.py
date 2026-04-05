# preferences.py

from gi.repository import Gtk, Adw, GLib, Gst, Gio, GObject

from .integrations import get_current_integration
from .constants import SIDEBAR_MENU
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/preferences.ui')
class NocturnePreferences(Adw.PreferencesDialog):
    __gtype_name__ = 'NocturnePreferencesDialog'

    context_button_el = Gtk.Template.Child()
    show_playlists_sidebar_el = Gtk.Template.Child()
    dynamic_bg_el = Gtk.Template.Child()
    blur_bg_el = Gtk.Template.Child()
    default_page_el = Gtk.Template.Child()

    restore_el = Gtk.Template.Child()
    hide_on_close_el = Gtk.Template.Child()

    hp_songs_el = Gtk.Template.Child()
    hp_albums_el = Gtk.Template.Child()
    hp_artists_el = Gtk.Template.Child()
    hp_playlists_el = Gtk.Template.Child()

    session_group_el = Gtk.Template.Child()
    instance_avatar_el = Gtk.Template.Child()
    instance_icon_el = Gtk.Template.Child()
    instance_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        settings = Gio.Settings.new("com.jeffser.Nocturne")

        settings.bind(
            "show-context-button",
            self.context_button_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "show-playlists-in-sidebar",
            self.show_playlists_sidebar_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "use-dynamic-background",
            self.dynamic_bg_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "player-blur-bg",
            self.blur_bg_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )

        # Default Page
        self.default_page_dict = {}
        selected_page = settings.get_value('default-page-tag').unpack()
        for section in SIDEBAR_MENU:
            for item in section.get('items', []):
                if section.get('title') and item.get('page-tag') != "radios":
                    title = '{} ({})'.format(section.get('title'), item.get('title'))
                else:
                    title = item.get('title')
                self.default_page_dict[title] = item.get('page-tag')
                self.default_page_el.get_model().append(title)
                if item.get('page-tag') == selected_page:
                    self.default_page_el.set_selected(len(self.default_page_dict) - 1)

        settings.bind(
            "restore-session",
            self.restore_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "hide-on-close",
            self.hide_on_close_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )

        settings.bind(
            "n-songs-home",
            self.hp_songs_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "n-albums-home",
            self.hp_albums_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "n-artists-home",
            self.hp_artists_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "n-playlists-home",
            self.hp_playlists_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )

        if integration := get_current_integration():
            data = integration.getServerInformation()
            self.instance_el.set_title(data.get('username', ""))

            self.instance_el.set_subtitle(data.get('title', ""))

            self.instance_el.set_tooltip_text(data.get('link'))
            self.instance_el.set_action_target_value(GLib.Variant('s', data.get('link', '')))
            self.instance_icon_el.set_visible(data.get('link'))
            self.instance_el.set_activatable(data.get('link'))

            self.instance_avatar_el.set_custom_image(data.get('picture'))
            self.instance_avatar_el.set_text(data.get('username', ''))
            self.instance_el.set_visible(len(data) > 0)
            self.session_group_el.set_visible(True)
        else:
            self.session_group_el.set_visible(False)

    @Gtk.Template.Callback()
    def on_dynamic_bg_toggled(self, row, gparam):
        if self.get_root():
            if row.get_active():
                if integration := get_current_integration():
                    if song_id := integration.loaded_models.get('currentSong').get_property('songId'):
                        if song_model := integration.loaded_models.get(song_id):
                            if raw_bytes := song_model.get_property('gdkPaintableBytes'):
                                thread = threading.Thread(
                                    target=self.get_root().playing_page.update_palette,
                                    args=(bytes(raw_bytes.get_data()),)
                                )
                                GLib.idle_add(thread.start)
            else:
                self.get_root().remove_css_class('dynamic-accent-bg')
                            
    @Gtk.Template.Callback()
    def on_blur_bg_toggled(self, row, gparam):
        if self.get_root():
            if row.get_active():
                self.get_root().add_css_class('player-blur')
            else:
                self.get_root().remove_css_class('player-blur')

    @Gtk.Template.Callback()
    def default_page_changed(self, combo_row, ud):
        page_tag = self.default_page_dict.get(combo_row.get_selected_item().get_string(), 'home')
        Gio.Settings.new("com.jeffser.Nocturne").set_string('default-page-tag', page_tag)

