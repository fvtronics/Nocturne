# page_dialog.py

from gi.repository import Gtk, Adw, GLib

@Gtk.Template(resource_path='/com/jeffser/Nocturne/containers/page_dialog.ui')
class PageDialog(Adw.Dialog):
    __gtype_name__ = 'NocturnePageDialog'

    navigation_view = Gtk.Template.Child()

    def __init__(self, page:Adw.NavigationPage):
        super().__init__()
        self.navigation_view.replace([page])
        
