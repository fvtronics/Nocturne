# downloads_queue_button.py

from gi.repository import Gtk, Adw, Gio
from ...integrations import get_current_integration
from .download_row import DownloadRow

@Gtk.Template(resource_path='/com/jeffser/Nocturne/containers/downloads_queue_button.ui')
class DownloadsQueueButton(Gtk.MenuButton):
    __gtype_name__ = 'NocturneDownloadsQueueButton'

    download_list_el = Gtk.Template.Child()

    def setup(self):
        integration = get_current_integration()
        model = integration.loaded_models.get('currentSong').get_property('downloadQueueModel')
        self.download_list_el.bind_model(
            model,
            lambda model: DownloadRow(model)
        )
        model.connect('notify::n-items', lambda model, ud: self.downloadQueueModelChanged(model))
        self.downloadQueueModelChanged(model)


    def downloadQueueModelChanged(self, model):
        self.set_visible(len(model) > 0)
