from traceback import print_exc
import rumps
from yanko.core.thread import StoppableThread
from yanko.sonic import (
    ArtistAlbums,
    Command,
    MostPlayed,
    Playlist,
    AlbumPlaylist,
    NowPlaying,
    LastAdded,
    RecentlyPlayed,
    Search,
    Status,
    Playstatus,
    ScanStatus,
    VolumeStatus
)
from yanko.ui.models import (
    ActionItem,
    Symbol,
    Label,
    MusicItem,
    ProgressIcon,
    AnimatedIcon
)
from yanko.sonic.manager import Manager
from yanko.ui.items.playlist import Playlist
from yanko.ui.items.albumlist import Albumlist, ArtistAlbumsList
from yanko.ui.items.nowplaying import NowPlayingItem
import logging
from yanko.api.server import Server
from yanko.lametric import LaMetric
from pathlib import Path


PausingIcon = AnimatedIcon(icons=[
    Symbol.GRID1, Symbol.GRID4
])

PlayingIcon = AnimatedIcon(icons=[
    Symbol.GRID1, Symbol.GRID2, Symbol.GRID3, Symbol.GRID4
])


class YankoAppMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def quit(cls):
        cls().terminate()


class YankoApp(rumps.App, metaclass=YankoAppMeta):

    manager: Manager = None
    __playlist: Playlist = None
    __last_added: Albumlist = None
    __artist_albums: Albumlist = None
    __recent: Albumlist = None
    __most_played: Albumlist = None
    __nowPlayingSection = []
    __threads = []
    __status: Status = None
    __nowplaying: NowPlaying = None
    __volume: VolumeStatus = None

    def __init__(self):
        super(YankoApp, self).__init__(
            name="yAnKo",
            menu=[
                ActionItem.random,
                ActionItem.random_album,
                None,
                ActionItem.artist,
                ActionItem.recent,
                ActionItem.last_added,
                ActionItem.most_played,
                None,
                ActionItem.previous,
                ActionItem.restart,
                ActionItem.next,
                None,
                ActionItem.rescan,
                ActionItem.quit
            ],
            icon=Symbol.STOPPED.value,
            quit_button=None,
            template=True
        )
        self.menu.setAutoenablesItems = False
        self.__status = Status.STOPPED
        self.__playlist = Playlist(self, Label.RANDOM.value)
        self.__last_added = Albumlist(self, Label.LAST_ADDED.value)
        self.__artist_albums = ArtistAlbumsList(self, Label.ARTIST.value)
        self.__most_played = Albumlist(self, Label.MOST_PLAYED.value)
        self.__recent = Albumlist(self, Label.RECENT.value)
        ActionItem.next.hide()
        ActionItem.restart.hide()
        ActionItem.previous.hide()
        self.manager = Manager()
        t = StoppableThread(target=self.manager.start, args=[
            self.onManagerResult,
            self.onPlayerResult
        ])
        t.start()
        self.__threads.append(t)
        ts = StoppableThread(target=Server.start, args=[
            self.manager.commander,
            self._onLaMetricInit
        ])
        ts.start()
        self.__threads.append(ts)
        self.manager.commander.put_nowait((Command.LAST_ADDED, None))
        self.manager.commander.put_nowait((Command.RECENTLY_PLAYED, None))
        self.manager.commander.put_nowait((Command.MOST_PLAYED, None))

    @property
    def threads(self):
        return self.__threads

    @rumps.clicked(Label.RANDOM.value)
    def onRandom(self, sender):
        self.manager.commander.put_nowait((Command.RANDOM, None))

    @rumps.clicked(Label.RANDOM_ALBUM.value)
    def onRandomAlbum(self, sender):
        self.manager.commander.put_nowait((Command.RANDOM_ALBUM, None))

    @rumps.clicked(Label.QUIT.value)
    def onQuit(self, sender):
        self.manager.commander.put_nowait((Command.QUIT, None))

    @rumps.clicked(Label.NEXT.value)
    def onNext(self, sender):
        self.manager.commander.put_nowait((Command.NEXT, None))

    @rumps.clicked(Label.PREVIOUS.value)
    def onPrevious(self, sender):
        self.manager.commander.put_nowait((Command.PREVIOUS, None))

    @rumps.clicked(Label.RESTART.value)
    def onRestart(self, sender):
        self.manager.commander.put_nowait((Command.RESTART, None))

    @rumps.clicked(Label.RESCAN.value)
    def onRescan(self, sender):
        self.manager.commander.put_nowait((Command.RESCAN, None))

    @rumps.events.on_screen_sleep
    def sleep(self):
        pass

    @rumps.events.on_screen_wake
    def wake(self):
        pass

    @rumps.timer(0.2)
    def updatePlayingTime(self, sender):
        match(self.__status):
            case Status.PLAYING:
                self.icon = next(PlayingIcon).value
            case Status.PAUSED:
                self.icon = next(PausingIcon).value
        # if self.__volume and self.__volume.hasExpired:
        #     self.__volume = None
        #     if self.__status == Status.PLAYING:
        #         self.title = self.__nowplaying.menubar_title
        #     else:
        #         self.title = ''

    def onManagerResult(self, resp):
        logging.debug(resp)

    def onPlayerResult(self, resp):
        method = f"_on{resp.__class__.__name__}"
        if hasattr(self, method):
            getattr(self, method)(resp)

    def _onNowPlaying(self, resp: NowPlaying):
        track = resp.track
        self.__nowplaying = resp
        LaMetric.nowplaying(
            f"{track.artist} / {track.title}", Path(track.coverArt))
        self.title = resp.menubar_title
        self.__playlist.setNowPlaying(track)
        for itm in self.__nowPlayingSection:
            self._menu.pop(itm)
        top = self.menu.keys()[0]
        self.__nowPlayingSection = [
            self.menu.insert_before(top, NowPlayingItem(
                track, callback=self._onNowPlayClick)),
            self.menu.insert_before(top, None)
        ]
        self.manager.commander.put_nowait(
            (Command.ARTIST_ALBUMS, resp.track.artistId))
        self.manager.commander.put_nowait(
            (Command.RECENTLY_PLAYED, None))

    def _onLaMetricInit(self):
        if self.__status in [Status.PLAYING] and self.__nowplaying:
            track = self.__nowplaying.track
            LaMetric.nowplaying(
                f"{track.artist} / {track.title}", Path(track.coverArt))
        return LaMetric.send_status(self.__status)

    def _onSearch(self, resp: Search):
        Server.queue(resp.queue_id).put_nowait(resp.to_dict())

    def _onPlaylist(self, resp: Playlist):
        list = resp.tracks
        self.__playlist.update(list, self._onPlaylistItem)

    def _onAlbumPlaylist(self, resp: AlbumPlaylist):
        list = resp.tracks
        self.__playlist.update(list, self._onPlaylistItem, True)

    def _onPlaylistItem(self, sender):
        self.manager.commander.put_nowait((Command.SONG, sender.id))

    def _onNowPlayClick(self, sender: NowPlayingItem):
        self.manager.commander.put_nowait((Command.TOGGLE, None))

    def _onAlbumClick(self, sender: MusicItem):
        self.manager.commander.put_nowait((Command.ALBUM, sender.id))

    def _onArtistClick(self, sender: MusicItem):
        self.manager.commander.put_nowait((Command.ARTIST, sender.id))

    def _onScanStatus(self, sender: ScanStatus):
        item: ActionItem = self.menu.get(Label.RESCAN.value)
        item.setAvailability(not sender.scanning)
        if not sender.scanning:
            self.manager.commander.put_nowait((Command.LAST_ADDED, None))

    def _onPlaystatus(self, resp: Playstatus):
        self.__status = resp.status
        LaMetric.status(resp.status)
        if resp.status == Status.PLAYING:
            if len(self.__playlist):
                ActionItem.next.show()
                ActionItem.previous.show()
            ActionItem.restart.show()
        elif resp.status == Status.STOPPED:
            self.icon = Symbol.STOPPED.value
            self.title = ''
            if len(self.__playlist):
                ActionItem.next.show()
                ActionItem.previous.show()
            else:
                ActionItem.next.hide()
                ActionItem.previous.hide()
            ActionItem.restart.hide()
        elif resp.status == Status.EXIT:
            rumps.quit_application()

    def _onVolumeStatus(self, resp: VolumeStatus):
        self.__volume = resp
        if self.__status == Status.PLAYING:
            self.title = f"{self.__nowplaying.menubar_title} [VOLUME {self.__volume.volume:.02f}]"
        else:
            self.title = 'V:{self.__volume}'

    def _onLastAdded(self, resp: LastAdded):
        albums = resp.albums
        self.__last_added.update(albums, self._onAlbumClick)

    def _onRecentlyPlayed(self, resp: RecentlyPlayed):
        albums = resp.albums
        self.__recent.update(albums, self._onAlbumClick)

    def _onMostPlayed(self, resp: MostPlayed):
        albums = resp.albums
        self.__most_played.update(albums, self._onAlbumClick)

    def _onArtistAlbums(self, resp: ArtistAlbums):
        albums = resp.albums
        artistInfo = resp.artistInfo
        self.__artist_albums.update(
            artistInfo, albums, self._onAlbumClick, self._onArtistClick)

    @rumps.events.before_quit
    def terminate(self):
        self.manager.commander.put_nowait((Command.QUIT, None))
        for th in self.__threads:
            try:
                th.stop()
            except Exception as e:
                print_exc(e)
                pass
        try:
            rumps.quit_application()
        except Exception as e:
            print_exc(e)
