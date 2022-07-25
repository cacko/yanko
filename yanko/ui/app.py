from queue import LifoQueue
import rumps
from threading import Thread
from yanko.sonic import (
    Command,
    Playlist,
    NowPlaying,
    LastAdded,
    RecentlyPlayed,
    Search,
    Status,
    Playstatus
)
from yanko.ui.models import (
    ActionItem,
    Icon,
    Label,
    MusicItem,
)
from yanko.sonic.manager import Manager
from yanko.ui.items.playlist import Playlist
from yanko.ui.items.albumlist import Albumlist
from yanko.ui.items.nowplaying import NowPlayingItem
import logging
from yanko.core.string import truncate
from yanko.api.server import Server



class YankoApp(rumps.App):

    manager: Manager = None
    __nowPlaying: NowPlaying = None
    __playlist: Playlist = None
    __last_added: Albumlist = None
    __recent: Albumlist = None
    __nowPlayingSection = []

    def __init__(self):
        super(YankoApp, self).__init__(
            name="yAnKo",
            menu=[
                ActionItem.random,
                ActionItem.artist,
                ActionItem.recent,
                ActionItem.newest,
                None,
                ActionItem.play,
                ActionItem.stop,
                ActionItem.next,
                ActionItem.restart,
                None,
                ActionItem.quit
            ],
            icon=Icon.STOPPED.value,
            quit_button=None,
            template=False
        )
        self.menu.setAutoenablesItems = False
        self.__playlist = Playlist(self, Label.RANDOM.value)
        self.__last_added = Albumlist(self, Label.NEWEST.value)
        self.__recent = Albumlist(self, Label.RECENT.value)
        ActionItem.stop.hide()
        ActionItem.play.hide()
        ActionItem.next.hide()
        ActionItem.restart.hide()
        self.manager = Manager()
        t = Thread(target=self.manager.start, args=[
            self.onManagerResult,
            self.onPlayerResult
        ])
        t.start()
        ts = Thread(target=Server.start, args=[
            self.manager.commander,
        ])
        ts.start()
        self.manager.commander.put_nowait((Command.NEWEST, None))
        self.manager.commander.put_nowait((Command.RECENTLY_PLAYED, None))


    @rumps.clicked(Label.PLAY.value)
    def onStart(self, sender):
        pass

    @rumps.clicked(Label.STOP.value)
    def onStop(self, sender):
        pass

    @rumps.clicked(Label.RANDOM.value)
    def onRandom(self, sender):
        self.manager.commander.put_nowait((Command.RANDOM, None))

    @rumps.clicked(Label.QUIT.value)
    def onQuit(self, sender):
        self.manager.commander.put_nowait((Command.QUIT, None))

    @rumps.clicked(Label.NEXT.value)
    def onNext(self, sender):
        self.manager.commander.put_nowait((Command.NEXT, None))

    @rumps.clicked(Label.RESTART.value)
    def onRestart(self, sender):
        self.manager.commander.put_nowait((Command.RESTART, None))

    @rumps.events.on_screen_sleep
    def sleep(self):
        pass

    @rumps.events.on_screen_wake
    def wake(self):
        pass

    def onManagerResult(self, resp):
        logging.debug(resp)

    def onPlayerResult(self, resp):
        method = f"_on{resp.__class__.__name__}"
        if hasattr(self, method):
            getattr(self, method)(resp)

    def _onNowPlaying(self, resp: NowPlaying):
        self.__nowPlaying = resp
        track = resp.track
        self.title = f"{track.artist} / {truncate(track.title)}"
        self.__playlist.setNowPlaying(track)
        for itm in self.__nowPlayingSection:
            self._menu.pop(itm)
        top = self.menu.keys()[0]
        self.__nowPlayingSection = [
            self.menu.insert_before(top, NowPlayingItem(track, callback=self._onAlbumClick)),
            self.menu.insert_before(top, None)
        ]
        # rumps.notification(track.title, track.artist, track.album, icon=track.coverArt)

    def _onSearch(self, resp: Search):
        Server.queue.put_nowait(resp.to_dict())

    def _onPlaylist(self, resp: Playlist):
        list = resp.tracks
        self.__playlist.update(list, self._onPlaylistItem)

    def _onPlaylistItem(self, sender):
        self.manager.commander.put_nowait((Command.SONG, sender.id))

    def _onAlbumClick(self, sender: MusicItem):
        self.manager.commander.put_nowait((Command.ALBUM, sender.id))

    def _onPlaystatus(self, resp: Playstatus):
        if resp.status == Status.PLAYING:
            self.icon = Icon.PLAYING.value
            ActionItem.stop.show()
            ActionItem.play.hide()
            if len(self.__playlist):
                ActionItem.next.show()
            ActionItem.restart.show()
        elif resp.status == Status.STOPPED:
            self.icon = Icon.STOPPED.value
            ActionItem.stop.hide()
            if len(self.__playlist):
                ActionItem.play.show()
                ActionItem.next.show()
            else:
                ActionItem.play.hide()
                ActionItem.next.hide()
            ActionItem.restart.hide()
        elif resp.status == Status.EXIT:
            rumps.quit_application()

    def _onLastAdded(self, resp: LastAdded):
        albums = resp.albums
        self.__last_added.update(albums, self._onAlbumClick)     

    def _onRecentlyPlayed(self, resp: RecentlyPlayed):
        albums = resp.albums
        self.__recent.update(albums, self._onAlbumClick)
