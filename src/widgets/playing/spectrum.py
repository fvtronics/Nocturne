# spectrum.py

from gi.repository import Gtk, Gdk, GObject, GLib, Gio
from ...integrations import get_current_integration
from ...constants import SPECTRUM_BARS
from colorthief import ColorThief
import io, threading

class Spectrum(Gtk.DrawingArea):
    __gtype_name__ = 'NocturneSpectrum'

    def setup(self):
        integration = get_current_integration()
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")

        self.loaded_magnitudes = {}
        self.target_magnitudes = [0] * SPECTRUM_BARS
        self.current_magnitudes = [0] * SPECTRUM_BARS

        self.color = [0.2, 0.6, 0.9]
        self.speed = 0.02

        self.set_draw_func(self.on_draw)

        integration.connect_to_model('currentSong', 'buttonState', self.playback_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.on_timestamp_changed)
        integration.connect_to_model('currentSong', 'magnitudes', self.on_update_magnitudes)
        integration.connect_to_model('currentSong', 'songId', self.song_changed)

        self.settings.bind(
            "show-visualizer",
            self,
            "visible",
            Gio.SettingsBindFlags.DEFAULT
        )

        GLib.timeout_add(16, self.on_tick)

    def on_timestamp_changed(self, timestamp:float):
        if next_timestamp := min((k for k in self.loaded_magnitudes if k >= timestamp), default=None):
            self.target_magnitudes = self.loaded_magnitudes[next_timestamp]

    def on_update_magnitudes(self, magnitudes:list):
        if magnitudes:
            self.loaded_magnitudes[magnitudes[1]] = magnitudes[0]

    def on_tick(self):
        if self.get_visible():
            for i in range(len(self.target_magnitudes)):
                speed_modifier = self.speed * max(0.25, min(1, 10*abs(self.target_magnitudes[i] - self.current_magnitudes[i])))
                if self.target_magnitudes[i] >= self.current_magnitudes[i]:
                    self.current_magnitudes[i] = min(self.target_magnitudes[i], self.current_magnitudes[i] + speed_modifier)
                else:
                    self.current_magnitudes[i] = max(0, self.current_magnitudes[i] - speed_modifier)
            self.queue_draw()
        return True

    def on_draw(self, drawing_area, cr, width, height):
        if not self.current_magnitudes:
            return

        n = len(self.current_magnitudes)
        dx = width / (n - 1)

        cr.move_to(0, height)

        cr.line_to(0, height * (1 - self.current_magnitudes[0]))

        for i in range(n - 1):
            x1 = i * dx
            y1 = height * (1 - self.current_magnitudes[i])
            x2 = (i + 1) * dx
            y2 = height * (1 - self.current_magnitudes[i + 1])

            # Control points for smoothness
            xc = (x1 + x2) / 2
            cr.curve_to(xc, y1, xc, y2, x2, y2)

        cr.line_to(width, height)
        cr.close_path()

        cr.set_source_rgba(*self.color, 0.75)
        cr.fill_preserve()

    def song_changed(self, songId:str):
        def set_color(model):
            if gbytes := model.get_property('gdkPaintableBytes'):
                raw_bytes = bytes(gbytes.get_data())
                img_io = io.BytesIO(raw_bytes)
                self.color = [min((255-c)/255, 1) for c in ColorThief(img_io).get_color(quality=10)]

        integration = get_current_integration()
        if found_model := integration.loaded_models.get(songId):
            threading.Thread(target=set_color, args=(found_model,)).start()
        else:
            self.target_magnitudes = [0] * SPECTRUM_BARS
            self.loaded_magnitudes = {}

    def playback_changed(self, playbackState:str):
        if playbackState == "play":
            self.target_magnitudes = [0] * SPECTRUM_BARS
            self.loaded_magnitudes = {}
