# base.py

from gi.repository import Gtk, GLib, GObject, Gdk
from . import models
import requests

# DO NOT USE DIRECTLY
class Base(GObject.Object):
    __gtype_name__ = 'NocturneIntegrationBase'

    # For how to fill these checkout navidrome.py and local.py
    login_page_metadata = {}
    button_metadata = {}

    loaded_models = {'currentSong': models.CurrentSong()}

    def check_if_ready(self, row) -> bool:
        # gets called to see if it is ready to show login page
        return True

    def connect_to_model(self, id:str, parameter:str, callback:callable) -> str:
        connection_id = ""
        if id in self.loaded_models:
            connection_id = self.loaded_models[id].connect(
                'notify::{}'.format(parameter),
                lambda *_, parameter=parameter, id=id: GLib.idle_add(callback, self.loaded_models[id].get_property(parameter))
            )
            GLib.idle_add(callback, self.loaded_models[id].get_property(parameter))
        return connection_id

    def start_instance(self) -> bool:
        # always called in different thread, because it might take a couple of seconds to get started
        print('WARNING', 'start_instance', 'not implemented')
        return False

    def terminate_instance(self):
        # called when the instance is no longer used
        print('WARNING', 'terminate_instance', 'not implemented')

    def on_login(self):
        # gets called in different thread when the login is successful
        print('WARNING', 'on_login', 'not implemented')

    def get_stream_url(self, song_id:str) -> str:
        # should return a valid url for a gst stream
        print('WARNING', 'get_stream_url', 'not implemented')
        return ""

    def getRadioCoverArt(self, id:str=None) -> tuple:
        # should set GdkPaintable and gdkPaintableBytes from Model
        # should return GLib.Bytes, Gdk.Paintable (texture)
        print('WARNING', 'getRadioCoverArt', 'not implemented')
        return None, None

    def getCoverArt(self, id:str=None) -> tuple:
        # should set GdkPaintable and gdkPaintableBytes from Model
        # should return GLib.Bytes, Gdk.Paintable (texture)
        print('WARNING', 'getCoverArt', 'not implemented')
        return None, None

    def ping(self) -> bool:
        # return True if logged in and connection is successful
        print('WARNING', 'ping', 'not implemented')
        return False

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        print('WARNING', 'getAlbumList', 'not implemented')
        return []

    def getArtists(self, size:int=10) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        print('WARNING', 'getArtists', 'not implemented')
        return []

    def getPlaylists(self) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        print('WARNING', 'getPlaylists', 'not implemented')
        return []

    def verifyArtist(self, id:str, force_update:bool=False, use_threading:bool=True):
        # verifies that element is fully loaded with all it's metadata, should also call for getCoverArt
        print('WARNING', 'verifyArtist', 'not implemented')

    def verifyAlbum(self, id:str, force_update:bool=False, use_threading:bool=True):
        # verifies that element is fully loaded with all it's metadata, should also call for getCoverArt
        print('WARNING', 'verifyAlbum', 'not implemented')

    def verifyPlaylist(self, id:str, force_update:bool=False, use_threading:bool=True):
        # verifies that element is fully loaded with all it's metadata, should also call for getCoverArt
        print('WARNING', 'verifyPlaylist', 'not implemented')

    def verifySong(self, id:str, force_update:bool=False, use_threading:bool=True):
        # verifies that element is fully loaded with all it's metadata, should also call for getCoverArt or getRadioCoverArt
        print('WARNING', 'verifySong', 'not implemented')

    def star(self, id:str) -> bool:
        # stars an element, should return True if change is done
        print('WARNING', 'star', 'not implemented')
        return False

    def unstar(self, id:str) -> bool:
        # unstars an element, should return True if change is done
        print('WARNING', 'unstar', 'not implemented')
        return False

    def getPlayQueue(self) -> tuple:
        # returns the song ID to be played and a list of IDs
        print('WARNING', 'getPlayQueue', 'not implemented')
        return "", []

    def savePlayQueue(self, id_list:list, current:str, position:int) -> bool:
        # save the play queue for retrieving later, called on close, return True if ok
        print('WARNING', 'savePlayQueue', 'not implemented')
        return False

    def getSimilarSongs(self, id:str, count:int=20) -> list:
        # returns list of IDs of similar songs to id, if it can not be implemented just return the result of getRandomSongs
        print('WARNING', 'getSimilarSongs', 'not implemented')
        return []

    def getRandomSongs(self, size:int=20) -> list:
        # returns a list of song IDs
        print('WARNING', 'getRandomSongs', 'not implemented')
        return []

    def getLyrics(self, track_name:str, artist_name:str, album_name:str, duration:int) -> dict:
        # This uses the LRCLIB public API
        # Duration is in seconds
        response = requests.get('https://lrclib.net/api/get', params={
            'track_name': track_name,
            'artist_name': artist_name,
            'album_name': album_name,
            'duration': duration
        })
        return response.json()

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0) -> dict:
        # returns a dict with results trucated with the count and offset, the dict has keys for album, artist and song, the values are lists of IDs
        # for an example view local.py
        print('WARNING', 'search', 'not implemented')
        return {}

    def getInternetRadioStations(self) -> list:
        # returns a list of Song IDs with the property isRadio=True
        # make sure the id also exists in self.loaded_models, no need to be verified
        print('WARNING', 'getInternetRadioStations', 'not implemented')
        return []

    def createInternetRadioStation(self, name:str, streamUrl:str, homePageUrl:str) -> bool:
        # returns True if created successfully
        print('WARNING', 'createInternetRadioStation', 'not implemented')
        return False

    def updateInternetRadioStation(self, id:str, name:str, streamUrl:str, homePageUrl:str) -> bool:
        # returns True if updated successfully
        print('WARNING', 'updateInternetRadioStation', 'not implemented')
        return False

    def deleteInternetRadioStation(self, id:str) -> bool:
        # returns True if deleted successfully
        print('WARNING', 'deleteInternetRadioStation', 'not implemented')
        return False

    def createPlaylist(self, name:str=None, playlistId:str=None, songId:list=[]) -> str:
        # returns True if created successfully
        print('WARNING', 'createPlaylist', 'not implemented')
        return ""

    def updatePlaylist(self, playlistId:str, songIdToAdd:list=[], songIndexToRemove:list=[]) -> bool:
        # returns True if updated successfully
        print('WARNING', 'updatePlaylist', 'not implemented')
        return False

    def deletePlaylist(self, id:str) -> bool:
        # returns True if deleted successfully
        print('WARNING', 'deletePlaylist', 'not implemented')
        return False

    def scrobble(self, id:str):
        # the id is for a Song, this is how views are stored
        # called when a song is played
        print('WARNING', 'scrobble', 'not implemented')
    
