# welcome.py

from gi.repository import Gtk, Adw, Gio, GLib
from . import LoginDialog
from ...integrations import Local, Navidrome, NavidromeIntegrated, Jellyfin

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/welcome.ui')
class WelcomePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneWelcomePage'

    listbox_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        integrations = [Navidrome, NavidromeIntegrated, Jellyfin, Local]
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

    def option_selected(self, row, integration):
        integration = integration()
        if integration.check_if_ready(row):
            dialog = LoginDialog(integration)
            dialog.present(self.get_root())


