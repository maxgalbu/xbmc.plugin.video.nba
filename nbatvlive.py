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
        'User-Agent': "iPad",
    }
    body = urllib.urlencode({
        'id': "0", 
        'type': 'channel',
        'plid': vars.player_id,
    })

    try:
        request = urllib2.Request(url, body, headers)
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.HTTPError as e:
        log("nba live tv: failed getting url: %s %s" % (url, e.read()), xbmc.LOGDEBUG)
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to get a video URL. Are you logged in?,5000,)')
        return

    xml = parseString(str(content))
    video_url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
    log("nba live tv: video url is %s" % video_url, xbmc.LOGDEBUG)

    match = re.search('http://([^:]+)/([^?]+?)\?(.+)$', video_url)
    domain = match.group(1)
    arguments = match.group(2)
    querystring = match.group(3)

    livecookies = "nlqptid=%s" % (querystring)
    livecookiesencoded = urllib.quote(livecookies)
    log("nba live tv live cookie: %s %s" % (querystring, livecookies), xbmc.LOGDEBUG)

    video_url = "http://%s/%s?%s|Cookie=%s" % (domain, arguments, querystring, livecookiesencoded)

    item = xbmcgui.ListItem("NBA TV Live", path=video_url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
