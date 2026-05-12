# login.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...integrations import secret
from ...constants import DEFAULT_MUSIC_DIR
from ..containers import ContextContainer
import threading, time

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
    quick_connect_button_el = Gtk.Template.Child()

    def __init__(self, integration):
        super().__init__()
        self.integration = integration

        # Metadata
        metadata = self.integration.login_page_metadata
        self.status_page.set_icon_name(metadata.get('icon-name'))
        self.status_page.set_title(metadata.get('title') or _("Login"))
        self.status_page.set_description(metadata.get('description') or '')

        # Server Status
        if 'status' in metadata.get('entries', []):
            self.server_status_el.set_visible(True)
            self.integration.connect(
                'notify::serverRunning',
                lambda *p, integ=self.integration: self.server_status_el.set_subtitle(_("Running") if integ.get_property('serverRunning') else _("Not Running"))
            )
        else:
            self.server_status_el.set_visible(False)

        # Url
        self.url_el.set_visible('url' in metadata.get('entries', []))
        self.url_el.set_text(self.integration.get_property('url'))

        # Url Extra Options
        self.url_options_el.set_visible('trust-server' in metadata.get('entries', [])) # Change line if more options are added
        self.trust_server_el.set_visible('trust-server' in metadata.get('entries', []))

        # User
        self.user_el.set_visible('user' in metadata.get('entries', []))
        self.user_el.set_text(self.integration.get_property('user'))

        # Password
        self.password_el.set_visible('password' in metadata.get('entries', []))
        self.password_el.set_text('')

        # Directory
        self.directory_el.set_visible('library-dir' in metadata.get('entries', []))
        self.directory_el.set_subtitle(self.integration.get_property('libraryDir'))

        # Login Button
        self.login_button_el.set_label(metadata.get('login-label') or _("Login"))
        self.login_button_el.set_sensitive(True)

        # Quick Connect (Jellyfin)
        self.quick_connect_button_el.set_visible(self.integration.__gtype_name__ == 'NocturneIntegrationJellyfin')

        # Extra Menu
        self.extra_menu_el.set_visible('extra-menu' in metadata)
        self.extra_menu_el.set_tooltip_text(metadata.get('extra-menu', {}).get('title', _("Extra Menu")))
        self.extra_menu_el.get_popover().set_child(ContextContainer(metadata.get('extra-menu', {}).get('context', {}), ''))

    @Gtk.Template.Callback()
    def library_changed(self, row, gparam):
        if row.get_visible() and 'library-dir' in self.integration.login_page_metadata.get('entries'):
            self.integration.set_property('libraryDir', row.get_subtitle())
            self.integration.terminate_instance()
            threading.Thread(target=self.integration.start_instance, daemon=True).start()

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
        threading.Thread(target=self.get_root().get_application().try_login, args=(self.integration,), daemon=True).start()

    @Gtk.Template.Callback()
    def quick_connect_button_clicked(self, button):
        if self.integration.__gtype_name__ != 'NocturneIntegrationJellyfin':
            return

        def wait_confirmation(data, dialog):
            waited_turns = 0
            is_authenticated = False
            while not is_authenticated and dialog.get_root():
                is_authenticated = self.integration.checkQuickConnect(data.get('Secret'))
                if is_authenticated:
                    GLib.idle_add(dialog.close)
                    threading.Thread(target=self.get_root().get_application().try_login, args=(self.integration,), daemon=True).start()
                    break
                time.sleep(5)
                waited_turns += 1
                if waited_turns >= 5:
                    GLib.idle_add(dialog.close)
                    break

        def run():
            data = self.integration.initiateQuickConnect()
            dialog = Adw.AlertDialog(
                heading=_("Quick Connect"),
                body=data.get("Code") or _("Error getting code"),
                extra_child=Gtk.LinkButton(
                    label=_("Quick Connect Page"),
                    uri="{}/web/#/quickconnect".format(self.url_el.get_text())
                )
            )
            dialog.add_response(
                "cancel",
                _("Cancel")
            )
            dialog.set_close_response("cancel")
            GLib.idle_add(dialog.choose,
                self.get_root(),
                None,
                lambda *_: None
            )
            GLib.idle_add(threading.Thread(target=wait_confirmation, args=(data, dialog), daemon=True).start)

        threading.Thread(target=run, daemon=True).start()

