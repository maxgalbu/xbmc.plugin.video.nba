import json
import datetime, time
from datetime import timedelta
import urllib,urllib2
import xbmc,xbmcplugin,xbmcgui
from xml.dom.minidom import parseString
import re,os
import sys

from utils import *
from common import * 
import vars

def getGameUrl(video_id, video_type="archive"):
    log("cookies: %s %s" % (video_type, vars.cookies), xbmc.LOGDEBUG)

    url = 'http://watch.nba.com/nba/servlets/publishpoint'
    headers = { 
        'Cookie': vars.cookies, 
        'Content-type': 'application/x-www-form-urlencoded',
        'User-Agent': 'iPad' if video_type == "live" 
            else "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0",
    }
    body = { 
        'id': str(video_id), 
        'gt': video_type, 
        'type': 'game',
        'plid': vars.player_id
    }
    if video_type != "live":
        body['isFlex'] = 'true'
    else:
        body['nt'] = '1'
    body = urllib.urlencode(body)

    response, content = vars.http.request(url, 'POST', body=body, headers=headers)
    if response['status'] != "200":
        log("Failed to get video url. The url was %s, the content was %s" % (url, str(content)))
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to get a video URL. Are you logged in?,5000,)')
        return ''

    xml = parseString(str(content))
    link = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
    log(link, xbmc.LOGDEBUG)

    if video_type == "live":
        # transform the link
        match = re.search('http://([^:]+)/([^?]+?)\?(.+)$', link)
        domain = match.group(1)
        arguments = match.group(2)
        querystring = match.group(3)

        livecookies = "nlqptid=%s" % (querystring)
        livecookiesencoded = urllib.quote(livecookies)

        log("live cookie: %s %s" % (querystring, livecookies), xbmc.LOGDEBUG)

        full_video_url = "http://%s/%s?%s|Cookie=%s" % (domain, arguments, querystring, livecookiesencoded)
    else:
        # transform the link
        m = re.search('adaptive://([^/]+)(/[^?]+)\?(.+)$', link)
        domain = m.group(1)
        path = urllib.quote_plus(str(m.group(2)))
        arguments = m.group(3)
        http_link = "http://%s/play?url=%s&%s" % (domain, path, arguments)
        log(http_link, xbmc.LOGDEBUG)
        
        # Make the second request which will return video of a (now) hardcoded
        # quality 
        # NOTE: had to switch to urllib2, as httplib2 assumed that
        # because the port was 443 it should use SSL (although the protocol
        # was correctly set to http)
        try:
            opener = urllib2.build_opener()
            opener.addheaders.append(('Cookie', vars.cookies))
            f = opener.open(http_link)
            content = f.read()
            f.close()
        except:
            content = ""
            pass
    
        if not content:
            log("no xml response, try guessing the url", xbmc.LOGDEBUG)
            full_video_url = getGameUrlGuessing(video_id, link)
        else:
            log("parsing xml response: %s" % content, xbmc.LOGDEBUG)
            
            # parse the xml
            xml = parseString(str(content))
            all_streamdata = xml.getElementsByTagName("streamData")
            full_video_url = ''
            for streamdata in all_streamdata:
                video_height = streamdata.getElementsByTagName("video")[0].attributes["height"].value

                if int(video_height) == vars.target_video_height:
                    selected_video_path = streamdata.attributes["url"].value
                    selected_domain = streamdata.getElementsByTagName("httpserver")[0].attributes["name"].value
                    full_video_url = getGameUrl_m3u8("http://%s%s" % (selected_domain, selected_video_path))

                    if urllib.urlopen(full_video_url).getcode() != 200:
                        full_video_url = ""
                    break
        
        if not full_video_url:
            log("parsed xml but video not found, try guessing the url", xbmc.LOGDEBUG)
            full_video_url = getGameUrlGuessing(video_id, link)
        
    if full_video_url:
        log("the url of video %s is %s" % (video_id, full_video_url), xbmc.LOGDEBUG)

    return full_video_url

def getGameUrl_m3u8(full_video_url):
    m3u8_url = re.sub(r'\.mp4$', ".mp4.m3u8", full_video_url)
    if urllib.urlopen(m3u8_url).getcode() == 200:
        full_video_url = m3u8_url
    return full_video_url

def getGameUrlGuessing(video_id, adaptive_link):
    available_bitrates = {
        720: 3000,
        540: 1600,
        432: 1200,
        360: 800,
        224: 224,
    }
    target_bitrate = available_bitrates.get(vars.target_video_height, 1600)
    failsafe_bitrate = available_bitrates.get(360)

    matches = re.search('adaptive://([^?]+)\?.+$', adaptive_link)
    video_url = matches.group(1)
    video_url = video_url.replace(":443", "")

    target_video_url = getGameUrlByBitrate(target_bitrate, video_url)
    target_video_url = getGameUrl_m3u8("http://%s" % target_video_url)

    if urllib.urlopen(target_video_url).getcode() != 200:
        log("video of height %d not found, trying with height 360" % vars.target_video_height, xbmc.LOGDEBUG)

        target_video_url = getGameUrlByBitrate(failsafe_bitrate, video_url)
        target_video_url = getGameUrl_m3u8("http://%s" % target_video_url)

        if urllib.urlopen(target_video_url).getcode() != 200:
            log("failsafe bitrate video not found, bailing out", xbmc.LOGDEBUG)
            return ""

    return target_video_url

def getGameUrlByBitrate(target_bitrate, video_url):
    # replace whole_1_pc\whole_2_pc with whole_[number]_[bitrate]
    return re.sub("whole_([0-9]+)_pc", "whole_\1_"+str(target_bitrate), video_url)

def getGames(fromDate = '', video_type = "archive"):
    try:
        schedule = 'http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/' +fromDate +  '.js?t=' + "%d"  %time.time()
        log('Requesting %s' % schedule, xbmc.LOGDEBUG)

        # http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/2013/10_7.js?t=1381054350000
        req = urllib2.Request(schedule, None);
        response = str(urllib2.urlopen(req).read())
        js = json.loads(response[response.find("{"):])

        for game in js['games']:
            log(game, xbmc.LOGDEBUG)
            for details in game:
                h = details.get('h', '')
                v = details.get('v', '')
                game_id = details.get('id', '')
                game_start_date_est = details.get('d', '')
                game_start_date = details.get('st', '')
                game_end_date = details.get('et', '')
                vs = details.get('vs', '')
                hs = details.get('hs', '')
                gs = details.get('gs', '')

                try:
                    if game_start_date:
                        game_start_date = datetime.datetime.strptime(game_start_date, "%Y-%m-%dT%H:%M:%S.%f" )
                    if game_end_date:
                        game_end_date = datetime.datetime.strptime(game_end_date, "%Y-%m-%dT%H:%M:%S.%f" )
                except:
                    if game_start_date:
                        game_start_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(game_start_date, "%Y-%m-%dT%H:%M:%S.%f")))
                    if game_end_date:
                        game_end_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(game_end_date, "%Y-%m-%dT%H:%M:%S.%f")))

                #set game start date in the past if python can't parse the date
                #so it doesn't get flagged as live or future game and you can still play it
                #if a video is available
                if type(game_start_date) is not datetime.datetime:
                    game_start_date = datetime.datetime.now() + datetime.timedelta(-30)

                #if the end date is not available (for live games, mainly), 
                #set game end date to be 2 hours after the start of the game
                if type(game_end_date) is not datetime.datetime:
                    game_end_date = game_start_date + datetime.timedelta(hours=4)

                if game_id != '':
                    # Get pretty names for the team names
                    if v.lower() in vars.teams:
                        visitor_name = vars.teams[v.lower()]
                    else:
                        visitor_name = v
                    if h.lower() in vars.teams:
                        host_name = vars.teams[h.lower()]
                    else:
                        host_name = h

                    # Create the title
                    name = game_start_date_est[:10] + ' ' + visitor_name + ' vs ' + host_name
                    if vars.scores == '1':
                        name = name + ' ' + str(vs) + ':' + str(hs)

                    thumbnail_url = ("http://e1.cdnl3.neulion.com/nba/player-v4/nba/images/teams/%s.png" % h)

                    has_video = "video" in details
                    future_video = game_start_date > datetime.datetime.now()
                    live_video = game_start_date < datetime.datetime.now() < game_end_date

                    add_link = True
                    if video_type == "live" and not live_video:
                        add_link = False
                    elif video_type != "live" and live_video:
                        add_link = False
                    elif future_video or not has_video:
                        add_link = False

                    video_mode = ''
                    if future_video:
                        name = name + " (F)"
                    elif has_video == False:
                        name = name + " (NV)"
                    else:
                        video_mode = 'playgame'

                    if add_link == True:
                        url = "%s/%s" % (game_id, video_type)
                        real_url = vars.cache.get("videourl_%s_%s" % (video_type, game_id))
                        if real_url:
                            addVideoListItem(name, real_url, thumbnail_url)
                        else:
                            addListItem(name, url, video_mode, thumbnail_url)

    except Exception, e:
        xbmc.executebuiltin('Notification(NBA League Pass,'+str(e)+',5000,)')
        log(str(e))
        pass

def playGame(video_string):
    # Authenticate
    if vars.cookies == '':
        vars.cookies = login()

    # Decode the video string
    currentvideo_id, currentvideo_type = video_string.split("/")

    # Get the video url. 
    # Authentication is needed over this point!
    # addLink("getting the archive game video_id for game with id %s" % video_id,'','','')
    currentvideo_url = getGameUrl(currentvideo_id, currentvideo_type)
    if currentvideo_url:
        vars.cache.set("videourl_%s_%s" % (currentvideo_type, currentvideo_id), currentvideo_url)

        item = xbmcgui.ListItem(path=currentvideo_url)
        xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER).play(currentvideo_url, item)
    else:
        xbmc.executebuiltin('Notification(NBA League Pass,Video not found.,5000,)')

def gameLinks(mode, url, date2Use = None):
    try:
        if mode == "selectdate":
            tday = getDate()
        elif mode == "oldseason":
            tday = date2Use
        else:
            tday = datetime.nowEST()
            log("current date (america timezone) is %s" % str(tday), xbmc.LOGDEBUG)

        # parse the video type
        video_type = url

        day = tday.isoweekday()
        # starts on mondays
        tday = tday - timedelta(day -1)
        now = tday
        default = "%04d/%d_%d" % (now.year, now.month, now.day)
        if mode == "live" or mode == "thisweek" or mode == "selectdate" or mode == "oldseason":
            # addLink("asked to get games for %s %s" % (default, video_type),'','','')
            # print "Calling getGames with %s %s" %(default, video_type)
            getGames(default, video_type)
        elif mode == "lastweek":
            tday = tday - timedelta(7)
            now = tday
            default = "%04d/%d_%d" % (now.year, now.month, now.day)
            getGames(default, video_type)
        else:
            getGames(default, video_type)
        xbmcplugin.addSortMethod( handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    except:
        xbmcplugin.endOfDirectory(handle = int(sys.argv[1]),succeeded=False)
        return None

