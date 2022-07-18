import rumps
from threading import Thread
from queue import Queue
from yanko.sonic import (
    Command,
    Playlist,
    NowPlaying,
    Status,
    Playstatus
)
from yanko.ui.models import (
    ActionItem,
    Icon,
    Label,
    ToggleAction,
)
from yanko.sonic.manager import Manager
from yanko.core.date import elapsed_duration, seconds_to_duration

from yanko import app_config, log


class YankoApp(rumps.App):

    manager: Manager = None
    __nowPlaying: NowPlaying = None
    __playlist = []

    def __init__(self):
        super(YankoApp, self).__init__(
            name="yAnKo",
            menu=[
                ActionItem.random,
                None,
                ActionItem.play,
                ActionItem.stop,
                ActionItem.next,
                ActionItem.restart,
                None,
                ActionItem.quit
            ],
            icon=Icon.NOT_PLAYING.value,
            quit_button=None
        )
        self.menu.setAutoenablesItems = False
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

    @rumps.clicked(Label.PLAY.value)
    def onStart(self, sender):
        pass

    @rumps.clicked(Label.STOP.value)
    def onStop(self, sender):
        pass

    @rumps.clicked(Label.RANDOM.value)
    def onRandom(self, sender):
        self.manager.commander.put_nowait(Command.RANDOM)

    @rumps.clicked(Label.QUIT.value)
    def onQuit(self, sender):
        self.manager.commander.put_nowait(Command.QUIT)

    @rumps.clicked(Label.NEXT.value)
    def onNext(self, sender):
        self.manager.commander.put_nowait(Command.NEXT)

    @rumps.clicked(Label.RESTART.value)
    def onRestart(self, sender):
        self.manager.commander.put_nowait(Command.RESTART)

    @rumps.events.on_screen_sleep
    def sleep(self):
        pass

    @rumps.events.on_screen_wake
    def wake(self):
        pass

    def onManagerResult(self, resp):
        log.debug(resp)

    def onPlayerResult(self, resp):
        getattr(self, f"_on{resp.__class__.__name__}")(resp)

    def _onNowPlaying(self, resp: NowPlaying):
        self.__nowPlaying = resp
        track = resp.track
        self.title = f"{track.artist} / {track.title:.20s}"

    @rumps.timer(0.1)
    def updateTimer(self, sender):
        if self.__nowPlaying:
            track = self.__nowPlaying.track
            self.title = f"{track.artist} / {track.title:.20s}"

    def _onPlaylist(self, resp: Playlist):
        list = resp.tracks
        self.__playlist = list

    def _onPlaystatus(self, resp: Playstatus):
        if resp.status == Status.PLAYING:
            self.icon = Icon.PLAYING.value
            ActionItem.stop.show()
            ActionItem.play.hide()
            if len(self.__playlist):
                ActionItem.next.show()
            ActionItem.restart.show()
        elif resp.status == Status.STOPPED:
            self.icon = Icon.NOT_PLAYING.value
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
