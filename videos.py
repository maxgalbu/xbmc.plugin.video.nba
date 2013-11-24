import json
import datetime, time
from datetime import date
from datetime import timedelta
import urllib,urllib2
import xbmc,xbmcplugin,xbmcgui,xbmcaddon
from xml.dom.minidom import parseString
import re

from utils import *
import vars

def videoDateMenu(video_type):
    global date

    dates = []
    current_date = date.today() - timedelta(days=1)
    last_date = current_date - timedelta(days=7)
    while current_date - timedelta(days=1) > last_date:
        dates.append(current_date)
        current_date = current_date - timedelta(days=1)

    for date in dates:
        addListItem(str(date), str(date), 'videodate'+video_type, '', True)
    xbmcplugin.endOfDirectory(handle = int(sys.argv[1]),succeeded=False)

def videoMenu(date, video_type):
    log("videoMenu: date requested is %s" % date, xbmc.LOGDEBUG)

    selected_date = None
    try:
        selected_date = datetime.datetime.strptime(date, "%Y-%m-%d" )
    except:
        selected_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, "%Y-%m-%d")))

    base_url = "http://smbsolr.cdnak.neulion.com/solr/NBA/select/?"
    params = urllib.urlencode({
        "wt": "json",
        "json.wrf": "updateVideoBoxCallback",
        "q": ("game_i:3" if video_type == "highlights" else "cat:Nightly Top Plays") +
            " AND releaseDate:[%s TO %s]" % (selected_date.strftime('%Y-%m-%dT00:00:00.000000Z'), selected_date.strftime('%Y-%m-%dT23:59:59.000000Z')),
        "sort": "releaseDate desc",
        "start": 0,
        "rows": 20
    })

    url = base_url + params;
    log("videoMenu: %s: url of date is %s" % (video_type, url), xbmc.LOGDEBUG)

    response = urllib2.urlopen(url).read()
    response = response[response.find("{"):response.rfind("}")+1]
    log("videoMenu: response: %s" % response, xbmc.LOGDEBUG)

    jsonresponse = json.loads(response)

    for video in jsonresponse['response']['docs']:
        addListItem(url=str(video['sequence']), name=video['name'], mode='videoplay', iconimage='')

def videoPlay(video_id):
    url = 'http://watch.nba.com/nba/servlets/publishpoint'
    headers = { 
        'Cookie': vars.cookies, 
        'Content-type': 'application/x-www-form-urlencoded',
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0",
    }
    body = urllib.urlencode({
        'id': str(video_id), 
        'bitrate': 1600,
        'type': 'video',
        'plid': vars.player_id,
        'isFlex:': 'true',
    })

    request = urllib2.Request(url, headers=headers)
    response = urllib2.urlopen(request, body)
    content = response.read()

    if response.getcode() != 200:
        log("videoPlay: failed getting video url: %s %s" % (url, response), xbmc.LOGDEBUG)
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to get a video URL. Are you logged in?,5000,)')
        return ''

    xml = parseString(str(content))
    video_url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
    log("videoPlay: video url is %s" % video_url, xbmc.LOGDEBUG)

    #remove query string
    video_url = re.sub("\?[^?]+$", "", video_url)

    item = xbmcgui.ListItem(path=video_url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
