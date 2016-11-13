import threading
import xbmc
import time, urllib
from urlparse import urlparse, parse_qs

import utils
from nbatvlive import LiveTV
from shareddata import SharedData

class MyPlayer(xbmc.Player):

    def onPlayBackEnded(self):
        utils.log("Playback ENDED...")

        shared_data = SharedData()
        shared_data.set("playing", {})

    def onPlayBackStopped(self):
        utils.log("Playback STOPPED...")

        shared_data = SharedData()
        shared_data.set("playing", {})

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

        self.expires = 0
        self.last_refresh = time.time()
        self.player = MyPlayer()
        self.shared_data = SharedData()

    def refreshLiveUrl(self):
        if self.shared_data.get("playing.what") == "nba_tv_live":
            #True=force login (refresh cookie)
            video_url = LiveTV.getLiveUrl(True)
        elif self.shared_data.get("playing.what") == "nba_tv_episode":
            start_timestamp = self.shared_data.get("playing.data.start_timestamp")
            duration = self.shared_data.get("playing.data.duration")
            video_url = LiveTV.getEpisodeUrl(start_timestamp, duration)

        if video_url:
            self.readExpiresFromUrl(video_url)
            utils.log("Updating live url from service, new url (%s) and expire (%d)" 
                % (video_url, self.expires))

            self.player.play(video_url)

    def readExpiresFromUrl(self, url):
        url_parts = urlparse(url)

        #Parse query string to dictionary
        query_params = parse_qs(url_parts.query)

        #Get the hdnea param, where the "expires" param is
        hdnea_params = query_params.get("hdnea")[0]
        hdnea_params = hdnea_params.replace('~', '&')
        hdnea_params = urllib.unquote(hdnea_params)

        self.expires = parse_qs(hdnea_params).get("expires", 0)[0]
        self.expires = int(self.expires)

    def run(self):
        while True:
            try:
                current_playing_url = self.player.getPlayingFile()
                self.readExpiresFromUrl(current_playing_url)
                utils.log("Playing url: %s - playing cache: %s" % 
                    (current_playing_url, self.shared_data.get("playing")), xbmc.LOGDEBUG)
            except:
                pass

            if self.shared_data.get("playing.what"):
                #Wait second iteration before checking the expiration
                if self.shared_data.get("playing.second_iteration") != "1":
                    xbmc.sleep(2000);
                    self.shared_data.set("playing.second_iteration", "1")
                    continue;

                timestamp = time.time()

                #Avoid refreshing too fast, let at least one minute pass from the last refresh
                expire_timestamp = max(self.expires, self.last_refresh + 60)

                utils.log("%d seconds to url refresh" % (expire_timestamp - timestamp))
                if timestamp > expire_timestamp:
                    self.refreshLiveUrl()
                    self.last_refresh = timestamp

            xbmc.sleep(1000)

            if not self.should_keep_running():
                utils.log("Interrupting service loop")
                break 

def main():
    utils.log("starting service...")

    #Reset currently playing video
    shared_data = SharedData()
    shared_data.set("playing", {})

    polling_thread = PollingThread()
    polling_thread.start()

    if xbmc.__version__ >= '2.19.0':
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(100):
                break
    else:
        while not xbmc.abortRequested:
            xbmc.sleep(100)

    utils.log("stopping service..")

    polling_thread.stop()

if __name__ == "__main__":
    main()