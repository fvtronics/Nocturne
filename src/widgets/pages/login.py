# login.py

from gi.repository import Gtk, Adw, Gio, GLib
from ..playing import Player
from ...integrations import secret, set_current_integration, Navidrome, Local
from ...constants import get_navidrome_path, check_if_navidrome_ready, get_navidrome_env, DEFAULT_MUSIC_DIR
from ..containers import ContextContainer
import threading, subprocess

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/login.ui')
class LoginDialog(Adw.Dialog):
    __gtype_name__ = 'NocturneLoginDialog'

    toast_overlay = Gtk.Template.Child()
    server_status_el = Gtk.Template.Child()
    extra_menu_el = Gtk.Template.Child()
    status_page = Gtk.Template.Child()
    url_el = Gtk.Template.Child()
    url_options_el = Gtk.Template.Child()
    trust_server_el = Gtk.Template.Child()
    directory_el = Gtk.Template.Child()
    user_el = Gtk.Template.Child()
    password_el = Gtk.Template.Child()

    login_button_el = Gtk.Template.Child()

    def __init__(self, integration):
        super().__init__()
        self.integration = integration

        # Metadata
        metadata = self.integration.login_page_metadata
        self.status_page.set_icon_name(metadata.get('icon-name'))
        self.status_page.set_title(metadata.get('title') or _("Login"))
        self.status_page.set_description(metadata.get('description') or '')

        # Server Status
        if 'status' in metadata.get('entries'):
            self.server_status_el.set_visible(True)
            self.integration.connect(
                'notify::serverRunning',
                lambda *p, integ=self.integration: self.server_status_el.set_subtitle(_("Running") if integ.get_property('serverRunning') else _("Not Running"))
            )
        else:
            self.server_status_el.set_visible(False)

        # Url
        self.url_el.set_visible('url' in metadata.get('entries'))
        self.url_el.set_text(self.integration.get_property('url'))

        # Url Extra Options
        self.url_options_el.set_visible('trust-server' in metadata.get('entries')) # Change line if more options are added
        self.trust_server_el.set_visible('trust-server' in metadata.get('entries'))

        # User
        self.user_el.set_visible('user' in metadata.get('entries'))
        self.user_el.set_text(self.integration.get_property('user'))

        # Password
        self.password_el.set_visible('password' in metadata.get('entries'))
        self.password_el.set_text('')

        # Directory
        self.directory_el.set_visible('library-dir' in metadata.get('entries'))
        self.directory_el.set_subtitle(self.integration.get_property('libraryDir'))

        # Login Button
        self.login_button_el.set_label(metadata.get('login-label') or _("Login"))
        self.login_button_el.set_sensitive(True)

        # Extra Menu
        self.extra_menu_el.set_visible('extra-menu' in metadata)
        self.extra_menu_el.set_tooltip_text(metadata.get('extra-menu', {}).get('title', _("Extra Menu")))
        self.extra_menu_el.get_popover().set_child(ContextContainer(metadata.get('extra-menu', {}).get('context', {}), ''))

    @Gtk.Template.Callback()
    def library_changed(self, row, gparam):
        if row.get_visible() and 'library-dir' in self.integration.login_page_metadata.get('entries'):
            self.integration.set_property('libraryDir', row.get_subtitle())
            self.integration.terminate_instance()
            threading.Thread(target=self.integration.start_instance).start()

    @Gtk.Template.Callback()
    def open_local_directory(self, row):
        def response(dialog, result):
            if folder := dialog.select_folder_finish(result):
                row.set_subtitle(folder.get_path())

        initial_folder = Gio.File.new_for_path(row.get_subtitle() or DEFAULT_MUSIC_DIR)
        dialog = Gtk.FileDialog(
            title=_("Local Music Library"),
            initial_folder=initial_folder
        )
        dialog.select_folder(self.get_root(), None, response)

    @Gtk.Template.Callback()
    def server_restart_requested(self, row):
        row.set_sensitive(False)
        self.integration.terminate_instance()
        if self.integration.start_instance():
            row.set_subtitle(_("Restarted"))
            GLib.timeout_add(1000, row.set_subtitle, _("Running"))
        else:
            row.set_subtitle(_("Error"))
        row.set_sensitive(True)

    @Gtk.Template.Callback()
    def login_button_clicked(self, button=None):
        self.login_button_el.set_sensitive(False)
        self.integration.set_property('url', self.url_el.get_text())
        self.integration.set_property('trustServer', self.trust_server_el.get_active())
        self.integration.set_property('user', self.user_el.get_text())
        secret.store_password(self.password_el.get_text())
        self.integration.set_property('libraryDir', self.directory_el.get_subtitle())
        threading.Thread(target=self.get_root().get_application().try_login, args=(self.integration,)).start()
