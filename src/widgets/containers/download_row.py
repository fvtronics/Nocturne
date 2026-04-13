# download_row.py

from gi.repository import Gtk, Adw, Gio, GObject
from ...integrations import get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/containers/download_row.ui')
class DownloadRow(Gtk.ListBoxRow):
    __gtype_name__ = 'NocturneDownloadRow'

    title_label = Gtk.Template.Child()
    progressbar = Gtk.Template.Child()
    suffix_stack = Gtk.Template.Child()

    def __init__(self, model):
        self.model = model
        integration = get_current_integration()
        integration.verifySong(self.model.get_property('songId'))
        super().__init__()
        title = integration.loaded_models.get(self.model.get_property('songId')).get_property('title')
        self.title_label.set_label(title)
        self.set_tooltip_text(title)
        self.model.bind_property(
            "progress",
            self.progressbar,
            "fraction",
            GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
        )

    @Gtk.Template.Callback()
    def progressbar_frac_changed(self, progressbar, ud):
        if progressbar.get_fraction() == 1:
            self.suffix_stack.set_visible_child_name('done')
            progressbar.set_visible(False)
