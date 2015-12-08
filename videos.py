import json
import datetime, time
from datetime import timedelta
import urllib,urllib2
import xbmc,xbmcplugin,xbmcgui
from xml.dom.minidom import parseString
import re

from utils import *
from common import *
import vars

def videoDateMenu():
    video_tag = vars.params.get("video_tag")
    
    dates = []
    current_date = datetime.date.today() - timedelta(days=1)
    last_date = current_date - timedelta(days=7)
    while current_date - timedelta(days=1) > last_date:
        dates.append(current_date)
        current_date = current_date - timedelta(days=1)

    for date in dates:
        params = {'date': date, 'video_tag': video_tag}
        addListItem(name=str(date), url='', mode='videolist', iconimage='', 
            isfolder=True, customparams=params)
    xbmcplugin.endOfDirectory(handle = int(sys.argv[1]))

def videoMenu():
    addListItem('Top Plays', '', 'videodate', '', True, customparams={'video_tag':'top_plays'})
    addListItem('Shaqtin\' a fool', '', 'videolist', '', True, customparams={
        'video_tag': 'shaqtin', 
        'video_query': "shaqtin"
    })

def videoListMenu():
    date = vars.params.get("date");
    video_tag = vars.params.get("video_tag")
    video_query = vars.params.get("video_query")
    log("videoListMenu: date requested is %s, tag is %s" % (date, video_tag), xbmc.LOGDEBUG)

    if date:
        selected_date = None
        try:
            selected_date = datetime.datetime.strptime(date, "%Y-%m-%d" )
        except:
            selected_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, "%Y-%m-%d")))


    query = []
    if video_tag:
        query.append("tags:%s" % video_tag)
    if video_query:
        query.append("(%s)" % video_query)
    query = " OR ".join(query)

    #Add the date if passed from the menu
    if date:
        query += " AND releaseDate:[%s TO %s]" % (
            selected_date.strftime('%Y-%m-%dT00:00:00.000Z'), 
            selected_date.strftime('%Y-%m-%dT23:59:59.000Z')
        )
    

    base_url = "http://smbsolr.cdnak.neulion.com/solr_nbav6/nba/nba/usersearch/?"
    params = urllib.urlencode({
        "wt": "json",
        "json.wrf": "updateVideoBoxCallback",
        "q": query,
        "sort": "releaseDate desc",
        "start": 0,
        "rows": 20
    })

    url = base_url + params;
    log("videoListMenu: %s: url of date is %s" % (video_tag, url), xbmc.LOGDEBUG)

    response = urllib2.urlopen(url).read()
    response = response[response.find("{"):response.rfind("}")+1]
    log("videoListMenu: response: %s" % response, xbmc.LOGDEBUG)

    jsonresponse = json.loads(response)

    for video in jsonresponse['response']['docs']:
        name = video['name']
        if not date:
            name = "%s (%s)" % (name, video['releaseDate'])

        addListItem(url=str(video['sequence']), name=name, mode='videoplay', iconimage='')
    xbmcplugin.endOfDirectory(handle = int(sys.argv[1]))

def videoPlay():
    video_id = vars.params.get("url")

    url = 'http://watch.nba.com/nba/servlets/publishpoint'
    headers = { 
        'Cookie': vars.cookies, 
        'Content-type': 'application/x-www-form-urlencoded',
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0",
    }
    body = urllib.urlencode({
        'id': str(video_id), 
        'bitrate': 800,
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
    video_url = getGameUrlWithBitrate(video_url, "video")
    log("videoPlay: video url is %s" % video_url, xbmc.LOGDEBUG)

    #remove query string
    video_url = re.sub("\?[^?]+$", "", video_url)

    item = xbmcgui.ListItem(path=video_url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
