from queue import Empty, Queue
import pyperclip3 as pc
from threading import Thread
from typing import Optional, Any
import logging
from rumps import rumps
from yanko.player.bpm import BeatsStruct
from yanko.player.device import Device
from yanko.api.server import Server
from yanko.lametric import LaMetric, StatusFrame
from yanko.sonic import (
    AlbumPlaylist,
    ArtistAlbums,
    Command,
    LastAdded,
    MostPlayed,
    NowPlaying,
    Playlist,
    Playstatus,
    RecentlyPlayed,
    ScanStatus,
    Search,
    Share,
    Status,
    VolumeStatus,
)
from yanko.sonic.beats import Fetcher
from yanko.sonic.manager import Manager
from yanko.ui.icons import AnimatedIcon, Label, Symbol
from yanko.ui.items.actions import ActionItem, MusicItem
from yanko.ui.items.albumlist import Albumlist, ArtistAlbumsList
from yanko.ui.items.bpm import BPM, BPMEvent
from yanko.ui.items.nowplaying import NowPlayingItem
from yanko.ui.items.playlist import Playlist as UIPlaylist
from yanko.ui.items.servermenu import ServerMenu
from yanko.core.config import app_config
from yanko.core import pid_file
# from yanko.ui.preferences.environment import EnvironmentPane


LoadingIcon = AnimatedIcon(
    [Symbol.HOURGLASS, Symbol.HOURGLASS_BOTTOM, Symbol.HOURGLASS_TOP]
)


class YankoAppMeta(type):
    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def quit(cls):
        cls().terminate()


class YankoApp(rumps.App, metaclass=YankoAppMeta):

    __nowPlayingSection: list[str] = []
    __threads: list[Thread] = []
    __volume: Optional[VolumeStatus] = None

    def __init__(self):
        super(YankoApp, self).__init__(
            name="yAnKo",
            menu=[
                ActionItem.random,
                ActionItem.random_album,
                ActionItem.share_song,
                ActionItem.share_album,
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
                ServerMenu.register(
                    items=[
                        (Label.CACHE.value, Symbol.CACHE.value),
                        (Label.RESCAN.value, Symbol.RESCAN.value),
                    ],
                    callback=self.onServerMenuItem,
                ),
                ActionItem.quit,
            ],
            icon=Symbol.STOPPED.value,
            quit_button=None,
            template=True,
            nosleep=True,
        )
        Device.register()
        self.__status = Status.LOADING
        self.__initCommands = [
            (Command.LAST_ADDED, LastAdded),
            (Command.RECENTLY_PLAYED, RecentlyPlayed),
            (Command.MOST_PLAYED, MostPlayed),
        ]
        self.__ui_queue = Queue()
        self.menu.setAutoenablesItems = False  # type: ignore
        self.__playlist = UIPlaylist(Label.RANDOM.value, self)
        self.__last_added = Albumlist(self, Label.LAST_ADDED.value)
        self.__artist_albums = ArtistAlbumsList(self, Label.ARTIST.value)
        self.__most_played = Albumlist(self, Label.MOST_PLAYED.value)
        self.__recent = Albumlist(self, Label.RECENT.value)
        ActionItem.next.hide()
        ActionItem.restart.hide()
        ActionItem.previous.hide()
        self.__bpm = BPM(ui_queue=self.__ui_queue)
        self.__bpm.start()
        self.__threads.append(self.__bpm)
        self.manager = Manager(
            ui_queue=self.__ui_queue,
            time_event=self.__bpm.time_event,
        )
        self.manager.start()
        self.__threads.append(self.manager)
        api_server = Server()
        api_server.start(self.manager.commander, self._onLaMetricInit)
        self.__threads.append(api_server)
        fetcher = Fetcher.register(
            manager_queue=self.manager.commander,
            do_extract=app_config.get("beats", {}).get("extract", False)
        )
        fetcher.start()
        self.__threads.append(fetcher)
        for cmd, _ in self.__initCommands:
            self.manager.commander.put_nowait((cmd, None))

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

    @rumps.clicked(Label.SHARE_SONG.value)
    def onShareSong(self, sender):
        self.manager.commander.put_nowait((Command.SHARE, "id"))

    @rumps.clicked(Label.SHARE_ALBUM.value)
    def onShareAlbum(self, sender):
        self.manager.commander.put_nowait((Command.SHARE, "albumId"))

    def onServerMenuItem(self, sender):
        match (sender.title):
            case Label.RESCAN.value:
                self.manager.commander.put_nowait((Command.RESCAN, None))

    @rumps.events.on_screen_sleep
    def sleep(self):
        pass

    @rumps.events.on_screen_wake
    def wake(self):
        pass

    @rumps.timer(2)
    def updatePlayingTime(self, sender):
        if self.__volume and self.__volume.hasExpired:
            self.__volume = None
            if self.__status == Status.PLAYING:
                self.title = self.__nowplaying.menubar_title
            else:
                self.title = ""

    @rumps.timer(0.1)
    def process_ui_queue(self, sender):
        try:
            if self.__status == Status.LOADING:
                self.icon = next(LoadingIcon).value
            resp = self.__ui_queue.get_nowait()
            if resp:
                method = f"_on{resp.__class__.__name__}"
                if hasattr(self, method):
                    getattr(self, method)(resp)
                self.__ui_queue.task_done()
                self.__checkInit(resp)
        except Empty:
            pass

    def __checkInit(self, executed_Cmd: Any):
        if all([not len(self.__initCommands), self.__status == Status.LOADING]):
            self.__status = Status.STOPPED
        elif executed_Cmd.__class__ in [*map(lambda x: x[1], self.__initCommands)]:

            self.__initCommands = list(filter(
                lambda x: x[1] != executed_Cmd.__class__, self.__initCommands
            ))
            if not len(self.__initCommands):
                self._onPlaystatus(Playstatus(status=Status.STOPPED))

    def _onBPMEvent(self, resp: BPMEvent):
        if not resp.hasExpired:
            self.icon = resp.icon

    def _onNowPlaying(self, resp: NowPlaying):
        track = resp.track
        self.__bpm.now_playing = resp
        self.__nowplaying = resp
        LaMetric.nowplaying(f"{track.artist} / {track.title}", track.coverArt)
        self.title = resp.menubar_title
        for itm in self.__nowPlayingSection:
            try:
                del self.menu[itm]
            except KeyError:
                pass
        top = self.__playlist.insert_before
        self.__nowPlayingSection = [
            self.menu.insert_before(
                top, NowPlayingItem(resp, callback=self._onNowPlayClick)
            ),
            self.menu.insert_before(top, None),
        ]
        self.__playlist.setNowPlaying(resp.track)
        self.manager.commander.put_nowait((Command.ARTIST_ALBUMS, resp.track.artistId))
        self.manager.commander.put_nowait((Command.RECENTLY_PLAYED, None))

    def _onBeatsStruct(self, resp: BeatsStruct):
        try:
            assert self.__nowplaying
            assert self.__nowplaying.track.path == resp.path
            self.__nowplaying.beats = resp
            self.__bpm.now_playing = self.__nowplaying
            it = self.menu.get(self.__nowPlayingSection[0])
            assert isinstance(it, NowPlayingItem)
            it.update_bpm(self.__nowplaying)
        except (AssertionError, AttributeError):
            pass

    def _onShare(self, resp: Share):
        try:
            assert resp
            pc.copy(resp.url)
            logging.debug(f"Coppied {resp.url} to cluipboard")
        except Exception as e:
            logging.exception(e)

    def _onLaMetricInit(self):
        try:
            LaMetric.status(status=self.__status)
            if self.__status in [Status.PLAYING] and self.__nowplaying:
                track = self.__nowplaying.track
                assert track.coverArt
                LaMetric.nowplaying(f"{track.artist} / {track.title}", track.coverArt)
            return StatusFrame(status=self.__status.value).dict()
        except AssertionError as e:
            logging.debug(e)

    def _onSearch(self, resp: Search):
        Server.queue(resp.queue_id).put_nowait(resp.dict())

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
        item: ActionItem = ServerMenu.action(Label.RESCAN)  # type: ignore
        item.setAvailability(not sender.scanning)
        if not sender.scanning:
            self.manager.commander.put_nowait((Command.LAST_ADDED, None))

    def _onPlaystatus(self, resp: Playstatus):
        self.__status = resp.status
        LaMetric.status(resp.status)
        match resp.status:
            case Status.PAUSED:
                self.icon = Symbol.PAUSE.value
            case Status.PLAYING:
                if len(self.__playlist):
                    ActionItem.next.show()
                    ActionItem.previous.show()
                ActionItem.restart.show()
            case Status.ERROR:
                self.icon = Symbol.ERROR.value
            case Status.STOPPED:
                self.icon = Symbol.STOPPED.value
                self.title = ""
                if len(self.__playlist):
                    ActionItem.next.show()
                    ActionItem.previous.show()
                else:
                    ActionItem.next.hide()
                    ActionItem.previous.hide()
                ActionItem.restart.hide()
            case Status.LOADING:
                self.icon = next(LoadingIcon).value
            case Status.EXIT:
                rumps.quit_application()

    def _onVolumeStatus(self, resp: VolumeStatus):
        self.__volume = resp
        if self.__status == Status.PLAYING:
            self.title = f"{self.__nowplaying.menubar_title} [VOLUME {self.__volume.volume:.02f}]"
        else:
            self.title = f"V:{self.__volume.volume}"

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
        albums.reverse()
        artistInfo = resp.artistInfo
        logging.debug(f"_onArtistAlbums {resp}")
        self.__artist_albums.update_with_artist(
            artistInfo, albums, self._onAlbumClick, self._onArtistClick  # type: ignore
        )

    @rumps.events.before_quit
    def terminate(self):
        self.manager.commander.put_nowait((Command.QUIT, None))
        for th in self.__threads:
            try:
                th.stop()  # type: ignore
            except Exception:
                pass
        try:
            rumps.quit_application()
            pid_file.unlink(missing_ok=True)
        except Exception:
            pass
