# welcome.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...constants import get_navidrome_path, DEFAULT_MUSIC_DIR
from ...integrations import set_current_integration, get_available_integrations, Local, Navidrome, NavidromeIntegrated
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/welcome.ui')
class WelcomePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneWelcomePage'

    listbox_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        selected_local_folder = settings.get_value("integration-library-dir").unpack()
        if not selected_local_folder:
            settings.set_string("integration-library-dir", DEFAULT_MUSIC_DIR)

        GLib.idle_add(self.check_auto_login)

    def setup_page(self):
        integrations = [Navidrome, NavidromeIntegrated, Local]
        for integration in integrations:
            metadata = integration.button_metadata
            row = Adw.ActionRow(
                title=metadata.get('title', _("Integration")),
                subtitle=metadata.get('subtitle', ""),
                tooltip_text=metadata.get('title', _("Integration")),
                activatable=True
            )
            row.add_suffix(Gtk.Image(
                icon_name="go-next-symbolic",
                valign=Gtk.Align.CENTER
            ))
            row.connect('activated', self.option_selected, integration)
            self.listbox_el.append(row)

    def check_auto_login(self):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        selected_instance = settings.get_value("selected-instance-type").unpack()
        if not selected_instance:
            self.get_root().main_stack.set_visible_child_name('welcome')
            self.setup_page()
        elif integration := get_available_integrations().get(selected_instance):
            self.get_root().main_stack.set_visible_child_name('login')
            self.get_root().login_page.setup_page(integration())

    def option_selected(self, row, integration):
        integration = integration()
        if integration.check_if_ready(row):
            self.get_root().main_stack.set_visible_child_name('login')
            self.get_root().login_page.setup_page(integration)

