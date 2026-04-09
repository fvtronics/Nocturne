# equalizer_page.py

from gi.repository import Gtk, Adw, Gio

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/equalizer_page.ui')
class EqualizerPage(Gtk.ScrolledWindow):
    __gtype_name__ = 'NocturneEqualizerPage'

    container = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")

        for i in range(6):
            band = Gtk.Scale(
                inverted=True,
                orientation=Gtk.Orientation.VERTICAL,
                draw_value=True,
                adjustment=Gtk.Adjustment(
                    lower=-12.0,
                    upper=12.0,
                    value=0
                )
            )
            settings.bind(
                "eq-band-{}".format(i),
                band.get_adjustment(),
                "value",
                Gio.SettingsBindFlags.DEFAULT
            )
            band.add_mark(
                value=6,
                position=Gtk.PositionType.TOP,
                markup="6dB" if i == 0 else None
            )
            band.add_mark(
                value=0,
                position=Gtk.PositionType.TOP,
                markup="0dB" if i == 0 else None
            )
            band.add_mark(
                value=-6,
                position=Gtk.PositionType.TOP,
                markup="-6dB" if i == 0 else None
            )
            self.container.append(band)
