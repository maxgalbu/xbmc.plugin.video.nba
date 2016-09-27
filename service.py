import threading
import xbmc
import sched, time

import vars
import utils
from nbatvlive import LiveTV

class MyPlayer(xbmc.Player):

    def onPlayBackEnded(self):
        vars.cache.delete("playing")

    def onPlayBackStopped(self):
        vars.cache.delete("playing")

class BaseThread(threading.Thread):
    """ Convenience class for creating stoppable threads. """

    def __init__(self):
        threading.Thread.__init__(self)
        if hasattr(self, 'daemon'):
            self.daemon = True
        else:
            self.setDaemon(True)
        self._stopped_event = threading.Event()

        if not hasattr(self._stopped_event, 'is_set'):
            self._stopped_event.is_set = self._stopped_event.isSet

    @property
    def stopped_event(self):
        return self._stopped_event

    def should_keep_running(self):
        """Determines whether the thread should continue running."""
        return not self._stopped_event.is_set()

    def on_thread_stop(self):
        """Override this method instead of stop().
        stop() calls this method.
        This method is called immediately after the thread is signaled to stop.
        """
        pass

    def stop(self):
        """Signals the thread to stop."""
        self._stopped_event.set()
        self.on_thread_stop()

    def on_thread_start(self):
        """Override this method instead of start(). start()
        calls this method.
        This method is called right before this thread is started and this
        object's run() method is invoked.
        """
        pass

    def start(self):
        self.on_thread_start()
        threading.Thread.start(self)


class PollingThread(BaseThread):

    def __init__(self):
        super(PollingThread, self).__init__()

        self.scheduler = None
        self.player = MyPlayer()

    def updateLiveUrl(self):
        utils.log("updating live url from service")

        video_url = LiveTV.getLiveUrl()
        self.player.play(video_url)

    def cancelScheduler(self):
        utils.log("cancelling scheduler")
        self.scheduler.cancel(self.scheduler_event)
        del self.scheduler
        self.scheduler = None

    def callAfter(self, timeout, func):
        if not self.scheduler:
            utils.log("starting scheduler")

            def funcWrapper():
                utils.log("called wrapper scheduler")
                func()
                self.scheduler.enter(timeout, 1, funcWrapper, ())

            self.scheduler = sched.scheduler(time.time, xbmc.sleep)
            self.scheduler_event = self.scheduler.enter(timeout, 1, funcWrapper, ())
            self.scheduler.run()

    def run(self):
        while True:
            try:
                utils.log("Playing url: %s" % self.player.getPlayingFile())
            except:
                pass

            '''if vars.cache.get("playing") == "nba_tv_live" and not self.scheduler:
                self.callAfter(20, self.updateLiveUrl)
            elif not vars.cache.get("playing") and self.scheduler:
                self.cancelScheduler()'''

            xbmc.sleep(1000)

            if not self.should_keep_running():
                utils.log("interrupting loop")
                break 

def main():
    utils.log("starting...")

    vars.cache.delete("playing")

    polling_thread = PollingThread()
    polling_thread.start()

    if xbmc.__version__ >= '2.19.0':
        monitor = xbmc.Monitor()
        monitor.waitForAbort()
    else:
        while not xbmc.abortRequested:
            xbmc.sleep(100)

    utils.log("stopping..")

    polling_thread.stop()

if __name__ == "__main__":
    main()