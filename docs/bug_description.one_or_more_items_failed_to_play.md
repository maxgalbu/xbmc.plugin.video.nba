
## The behavior

When a user chooses a video, sometimes he gets an error message saying:

    "One or more items failed to play. Check the log file for details."

But then the playback works. What actually happens is that the plugin adds this playlist item:

    plugin://plugin.video.nba/?url=0021301069%2Fcondensed&mode=playgame&name=2014-03-26+Knicks+vs+Kings

The plugin then adds the actual video url in the playlist, which works. But the plugin playlist item actually fails, so we get the error.


### Why we get the error in the code

We get this error in the logs:

    10:42:16 T:140452728235904   ERROR: Playlist Player: skipping unplayable item: 0, path [plugin://plugin.video.nba/?url=0021301069%2Fcondensed&mode=playgame&name=2014-03-26+Knicks+vs+Kings]

This is logged by this line of xbmc/PlayListPlayer.cpp:

```c++
bool CPlayListPlayer::Play(int iSong, bool bAutoPlay /* = false */, bool bPlayPrevious /* = false */)
...

if ((m_iFailedSongs >= g_advancedSettings.m_playlistRetries && g_advancedSettings.m_playlistRetries >= 0)
    || ((XbmcThreads::SystemClockMillis() - m_failedSongsStart  >= (unsigned int)g_advancedSettings.m_playlistTimeout * 1000) && g_advancedSettings.m_playlistTimeout))
{
  CLog::Log(LOGDEBUG,"Playlist Player: one or more items failed to play... aborting playback");

  // open error dialog
  CGUIDialogOK::ShowAndGetInput(16026, 16027, 16029, 0);
```

The default value of m_playlistRetries is 100 and of m_playlistTimeout is 20 seconds. This is documented in [http://wiki.xbmc.org/?title=Media_Sources&action=edit&oldid=7392](http://wiki.xbmc.org/?title=Media_Sources&action=edit&oldid=7392). But what actually happens in ./xbmc/settings/AdvancedSettings.cpp is that the default value is set to 5 seconds.

So XBMC waits for 5 seconds for the plugin playlist item to work. If the video starts before that time then CPlayListPlayer::Play is called for the actual video and we do not get the error. If the video starts after the 5 seconds mark, we get the timeout and the error is sent to the user.

### A workaround

This suggests an obvious workaround, raise the timeout to 20 seconds in the [advancedsettings.xml](http://wiki.xbmc.org/index.php?title=Advancedsettings.xml):

```XML
<advancedsettings>
  <playlisttimeout>20</playlisttimeout> 
</advancedsettings>
```
