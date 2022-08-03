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
    Track
)
from yanko.ui.models import (
    ActionItem,
    Icon,
    Label,
    MusicItem
)
from yanko.sonic.manager import Manager
from yanko.ui.items.playlist import Playlist
from yanko.ui.items.albumlist import Albumlist, ArtistAlbumsList
from yanko.ui.items.nowplaying import NowPlayingItem
import logging
from yanko.core.string import truncate
from yanko.api.server import Server
from yanko.lametric import LaMetric
from pathlib import Path
from AppKit import NSImage
from AppKit import NSMakeRect
from AppKit import NSCompositingOperationSourceOver
from Foundation import NSMutableDictionary
from MediaPlayer import MPNowPlayingInfoCenter
from MediaPlayer import MPRemoteCommandCenter
from MediaPlayer import MPMediaItemArtwork
from MediaPlayer import MPMediaItemPropertyTitle
from MediaPlayer import MPMediaItemPropertyArtist
from MediaPlayer import MPMediaItemPropertyPlaybackDuration
from MediaPlayer import MPMediaItemPropertyArtwork
from MediaPlayer import MPMusicPlaybackState
from MediaPlayer import MPMusicPlaybackStatePlaying
from MediaPlayer import MPMusicPlaybackStatePaused
from MediaPlayer import MPMusicPlaybackStateStopped


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

    def __init__(self):
        super(YankoApp, self).__init__(
            name="yAnKo",
            menu=[
                ActionItem.random,
                ActionItem.random_album,
                None,
                ActionItem.artist,
                ActionItem.recent,
                ActionItem.newest,
                ActionItem.most_played,
                None,
                ActionItem.next,
                ActionItem.restart,
                None,
                ActionItem.rescan,
                ActionItem.quit
            ],
            icon=Icon.STOPPED.value,
            quit_button=None,
            template=False
        )
        self.menu.setAutoenablesItems = False
        self.__status = Status.STOPPED
        self.__playlist = Playlist(self, Label.RANDOM.value)
        self.__last_added = Albumlist(self, Label.NEWEST.value)
        self.__artist_albums = ArtistAlbumsList(self, Label.ARTIST.value)
        self.__most_played = Albumlist(self, Label.MOST_PLAYED.value)
        self.__recent = Albumlist(self, Label.RECENT.value)
        ActionItem.next.hide()
        ActionItem.restart.hide()
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
        self.manager.commander.put_nowait((Command.NEWEST, None))
        self.manager.commander.put_nowait((Command.RECENTLY_PLAYED, None))
        self.manager.commander.put_nowait((Command.MOST_PLAYED, None))

        self.cmd_center = MPRemoteCommandCenter.sharedCommandCenter()

        # Get the Now Playing Info Center
        # ... which is how this application notifies MacOS of what is playing
        self.info_center = MPNowPlayingInfoCenter.defaultCenter()

        # Enable Commands
        self.cmd_center.playCommand()           .addTargetWithHandler_(self.hPlay)
        self.cmd_center.pauseCommand()          .addTargetWithHandler_(self.hPause)
        self.cmd_center.togglePlayPauseCommand().addTargetWithHandler_(self.hTogglePause)
        self.cmd_center.nextTrackCommand()      .addTargetWithHandler_(self.hNextTrack)
        self.cmd_center.previousTrackCommand()  .addTargetWithHandler_(self.hPrevTrack)

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
        self.title = f"{track.artist} / {truncate(track.title)}"
        self.__playlist.setNowPlaying(track)
        for itm in self.__nowPlayingSection:
            self._menu.pop(itm)
        top = self.menu.keys()[0]
        self.__nowPlayingSection = [
            self.menu.insert_before(top, NowPlayingItem(
                track, callback=self._onNowPlayClick)),
            self.menu.insert_before(top, None)
        ]
        self.icon = resp.track.coverArtIcon
        self.manager.commander.put_nowait(
            (Command.ARTIST_ALBUMS, resp.track.artistId))
        self.onPlaying(track)
        # rumps.notification(track.title, track.artist, track.album, icon=track.coverArt)

    def _onLaMetricInit(self):
        if self.__status in [Status.PLAYING] and self.__nowplaying:
            track = self.__nowplaying.track
            LaMetric.nowplaying(
                f"{track.artist} / {track.title}", Path(track.coverArt))
        LaMetric.send_status(self.__status)

    def _onSearch(self, resp: Search):
        Server.queue.put_nowait(resp.to_dict())

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
            self.manager.commander.put_nowait((Command.NEWEST, None))

    def _onPlaystatus(self, resp: Playstatus):
        self.__status = resp.status
        LaMetric.status(resp.status)
        if resp.status == Status.PLAYING:
            if len(self.__playlist):
                ActionItem.next.show()
            ActionItem.restart.show()
        elif resp.status == Status.PAUSED:
            self.icon = Icon.PAUSE.value
        elif resp.status == Status.RESUMED:
            self.icon = self.__nowplaying.track.coverArtIcon
        elif resp.status == Status.STOPPED:
            self.icon = Icon.STOPPED.value
            self.title = ''
            if len(self.__playlist):
                ActionItem.next.show()
            else:
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

    def _onMostPlayed(self, resp: MostPlayed):
        albums = resp.albums
        self.__most_played.update(albums, self._onAlbumClick)

    def _onArtistAlbums(self, resp: ArtistAlbums):
        albums = resp.albums
        artistInfo = resp.artistInfo
        self.__artist_albums.update(
            artistInfo, albums, self._onAlbumClick, self._onArtistClick)

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

    def hPlay(self, event):
        """
        Handle an external 'playCommand' event
        """
        logging.info("on play")

        return 0

    def hPause(self, event):
        """
        Handle an external 'pauseCommand' event
        """
        logging.info("on pause")

        return 0

    def hTogglePause(self, event):
        """
        Handle an external 'togglePlayPauseCommand' event
        """
        logging.info("on toggle pause")

        return 0

    def hNextTrack(self, event):
        """
        Handle an external 'nextTrackCommand' event
        """
        logging.info("next")

        return 0

    def hPrevTrack(self, event):
        """
        Handle an external 'previousTrackCommand' event
        """
        logging.info("on prev")

        return 0

    def onStopped(self):
        """
        Call this method to update 'Now Playing' state to: stopped
        """
        self.info_center.setPlaybackState_(MPMusicPlaybackStateStopped)
        logging.info("on stopped")
        return 0

    def onPaused(self):
        """
        Call this method to update 'Now Playing' state to: paused
        """
        self.info_center.setPlaybackState_(MPMusicPlaybackStatePaused)
        return 0

    def onPlaying(self, track: Track):
        """
        Call this method to update 'Now Playing' state to: playing

        :param title: Track Title
        :param artist: Track Artist
        :param length: Track Length
        :param cover: Track cover art as byte array
        """

        title = track.title
        artist = track.artist
        length = track.duration


        logging.info("on now play")


        nowplaying_info = NSMutableDictionary.dictionary()

        # # Set basic track information
        nowplaying_info[MPMediaItemPropertyTitle]            = title
        nowplaying_info[MPMediaItemPropertyArtist]           = artist
        nowplaying_info[MPMediaItemPropertyPlaybackDuration] = length

        # # Set the cover art
        # # ... which requires creation of a proper MPMediaItemArtwork object
        # cover = ptr.record.cover
        # if cover is not None:
        #     # Apple documentation on how to load and set cover artwork is less than clear
        #     # The below code was cobbled together from numerous sources
        #     # ... REF: https://stackoverflow.com/questions/11949250/how-to-resize-nsimage/17396521#17396521
        #     # ... REF: https://developer.apple.com/documentation/mediaplayer/mpmediaitemartwork?language=objc
        #     # ... REF: https://developer.apple.com/documentation/mediaplayer/mpmediaitemartwork/1649704-initwithboundssize?language=objc

        #     img = NSImage.alloc().initWithData_(cover)

        #     def resize(size):
        #         new = NSImage.alloc().initWithSize_(size)
        #         new.lockFocus()
        #         img.drawInRect_fromRect_operation_fraction_(
        #             NSMakeRect(0, 0, size.width, size.height),
        #             NSMakeRect(0, 0, img.size().width, img.size().height),
        #             NSCompositingOperationSourceOver,