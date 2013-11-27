import json
import datetime, time
import urllib,urllib2
import xbmc,xbmcplugin,xbmcgui,xbmcaddon
from xml.dom.minidom import parseString
import re

from common import *
import vars

def playLiveTV():
    if not vars.cookies:
        login()

    url = 'http://watch.nba.com/nba/servlets/publishpoint'
    headers = { 
        'Cookie': vars.cookies, 
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36",
    }
    body = urllib.urlencode({
        'id': "0", 
        'type': 'channel',
        'plid': vars.player_id,
        'isFlex': "true",
    })

    try:
        request = urllib2.Request(url, body, headers)
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.HTTPError as e:
        log("nba live tv: failed getting url: %s %s" % (url, e.read()), xbmc.LOGDEBUG)
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to get a video URL. Are you logged in?,5000,)')
        return

    # Get the adaptive video url
    xml = parseString(str(content))
    video_adaptive_url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
    log("nba live tv: adaptive video url is %s" % video_adaptive_url, xbmc.LOGDEBUG)

    # Transform the link from adaptive://domain/url?querystring to
    # http://domain/play?url=url&querystring
    match = re.search('adaptive://([^/]+)(/[^?]+)\?(.+)$', video_adaptive_url)
    domain = match.group(1)
    path = urllib.quote_plus(str(match.group(2)))
    querystring = match.group(3)
    video_play_url = "http://%s/play?url=%s&%s" % (domain, path, querystring)
    log("nba live tv: play url is %s" % video_play_url, xbmc.LOGDEBUG)

    # Recreate the cookies from the query string
    video_cookies = "nlqptid=%s" % (querystring)
    video_cookies_encoded = urllib.quote(video_cookies)
    log("nba live tv: live cookie: %s" % video_cookies, xbmc.LOGDEBUG)

    # Get the video play url (which will return different urls for
    # different bitrates)
    try:
        request = urllib2.Request(video_play_url, None, {'Cookie': vars.cookies})
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.HTTPError as e:
        log("nba live tv: failed getting url: %s %s" % (video_play_url, e.read()))
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to get a video URL (response != 200),5000,)')
        return

    if not content:
        log("nba live tv: empty response from video play url")
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to get a video URL (response was empty),5000,)')
        return
    else:
        log("nba live tv: parsing response: %s" % content, xbmc.LOGDEBUG)

        # Parse the xml to find different bitrates
        xml = parseString(str(content))
        all_streamdata = xml.getElementsByTagName("streamData")
        video_url = ''
        for streamdata in all_streamdata:
            video_height = streamdata.getElementsByTagName("video")[0].attributes["height"].value

            if int(video_height) == vars.target_video_height:
                selected_video_path = streamdata.attributes["url"].value
                selected_domain = streamdata.getElementsByTagName("httpserver")[0].attributes["name"].value
                video_url = "http://%s%s.m3u8" % (selected_domain, selected_video_path)
                break

    # Add the cookies in the format "videourl|Cookie=[cookies]""
    video_url = "%s?%s|Cookie=%s" % (video_url, querystring, video_cookies_encoded)

    item = xbmcgui.ListItem("NBA TV Live", path=video_url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
