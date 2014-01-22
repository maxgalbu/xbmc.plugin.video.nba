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

def getGameUrl(video_id, video_type, video_ishomefeed):
    log("cookies: %s %s" % (video_type, vars.cookies), xbmc.LOGDEBUG)

    url = 'http://watch.nba.com/nba/servlets/publishpoint'
    headers = { 
        'Cookie': vars.cookies, 
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'iPad' if video_type == "live" 
            else "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0",
    }
    body = { 
        'id': str(video_id), 
        'gt': video_type + ("away" if not video_ishomefeed else ""), 
        'type': 'game',
        'plid': vars.player_id
    }
    if video_type != "live":
        body['isFlex'] = 'true'
    else:
        body['nt'] = '1'
    body = urllib.urlencode(body)

    log("the body of publishpoint request is: %s" % body, xbmc.LOGDEBUG)

    try:
        request = urllib2.Request(url, body, headers)
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.HTTPError as e:
        log("Failed to get video url. The url was %s, the content was %s" % (url, e.read()))
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
        
        selected_video_url = ''
        if not content:
            log("no xml response, try guessing the url", xbmc.LOGDEBUG)
            selected_video_url = getGameUrlGuessing(video_id, link)
        else:
            log("parsing xml response: %s" % content, xbmc.LOGDEBUG)
            
            # Parse the xml. The streamdata tag looks like this:
            # <streamData url="/nlds_vod/nba/vod/2014/01/15/21300566/a29e02/2_21300566_chi_orl_2013_h_condensed_1_3000.mp4" blockDuration="2000" bitrate="3072000" duration="1155121">
            #     <video width="1280" height="720" fps="29.970030" bitrate="2978816" codec="avc1" />
            #     <audio channelCount="2" samplesRate="44100" sampleBitSize="16" bitrate="124928" codec="mp4a" />
            #     <httpservers>
            #         <httpserver name="nlds120.cdnak.neulion.com" port="80" />
            #         <httpserver name="nlds120.cdnl3nl.neulion.com" port="80" />
            #     </httpservers>
            # </streamData>
            xml = parseString(str(content))
            all_streamdata = xml.getElementsByTagName("streamData")
            for streamdata in all_streamdata:
                video_height = streamdata.getElementsByTagName("video")[0].attributes["height"].value

                if int(video_height) == vars.target_video_height:
                    selected_video_path = streamdata.attributes["url"].value
                    http_servers = streamdata.getElementsByTagName("httpserver")
                    for http_server in http_servers:
                        server_name = http_server.attributes["name"].value
                        server_port = http_server.attributes["port"].value

                        # Construct the video url
                        mp4_video_url = "http://%s:%s%s" % (server_name, server_port, selected_video_path)
                        m3u8_video_url = getGameUrl_m3u8(mp4_video_url)
                        
                        # Test if the video is actually available. If it is not available go to the next server.
                        # The mp4 urls rarely work
                        if urllib.urlopen(m3u8_video_url).getcode() == 200:
                            selected_video_url = m3u8_video_url
                            break

                        log("no working url found for this server, moving to the next", xbmc.LOGDEBUG)

                    # break from the video quality loop
                    break
        
        if not selected_video_url:
            log("parsed xml but video not found, try guessing the url", xbmc.LOGDEBUG)
            selected_video_url = getGameUrlGuessing(video_id, link)
        
    if selected_video_url:
        log("the url of video %s is %s" % (video_id, selected_video_url), xbmc.LOGDEBUG)

    return selected_video_url

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
    video_url = video_url.replace(":443", "", 1)

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
                vs = details.get('vs', '')
                hs = details.get('hs', '')
                gs = details.get('gs', '')

                video_has_away_feed = False
                if video_type != "condensed":
                    video_details = details.get('video', {})
                    video_has_away_feed = video_details.get("af", False)

                # Try to convert start date to datetime
                try:
                    game_start_datetime_est = datetime.datetime.strptime(game_start_date_est, "%Y-%m-%dT%H:%M:%S.%f" )
                except:
                    game_start_datetime_est = datetime.datetime.fromtimestamp(time.mktime(time.strptime(game_start_date_est, "%Y-%m-%dT%H:%M:%S.%f")))

                #et game start date in the past if python can't parse the date
                #so it doesn't get flagged as live or future game and you can still play it
                #if a video is available
                if type(game_start_datetime_est) is not datetime.datetime:
                    game_start_datetime_est = nowEST() + timedelta(-30)

                #guess end date by adding 4 hours to start date
                game_end_datetime_est = game_start_datetime_est + timedelta(hours=4)

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
                    future_video = game_start_datetime_est > nowEST()
                    live_video = game_start_datetime_est < nowEST() < game_end_datetime_est

                    add_link = True
                    if video_type == "live" and not live_video:
                        add_link = False
                    elif video_type != "live" and live_video:
                        add_link = False
                    elif future_video or not has_video:
                        add_link = False

                    if add_link == True:
                        url = "%s/%s" % (game_id, video_type)

                        # If the game has home/away feeds, add a directory item
                        # that allows the user to select the home or away feed
                        if video_has_away_feed:
                            addListItem(name, url, "gamehomeaway", thumbnail_url, True)
                        else:
                            # Get the cached url for home feeds which is the default.
                            cached_url = vars.cache.get("videourl_%s_%s_1" % (video_type, game_id))
                            if cached_url:
                                addVideoListItem(name, cached_url, thumbnail_url)
                            else:
                                addListItem(name, url, "playgame", thumbnail_url)

    except Exception, e:
        xbmc.executebuiltin('Notification(NBA League Pass,'+str(e)+',5000,)')
        log(str(e))
        pass

def playGame(video_string):
    # Authenticate
    if vars.cookies == '':
        vars.cookies = login()

    # Decode the video string
    if video_string.count('/') == 2:
        # If the game has home/away feed, the "video_string" variable will have
        # the following format video_id/video_type/is_home_feed
        # where is_home_feed is 1 for "home" feed and "0" is for away feed 
        currentvideo_id, currentvideo_type, currentvideo_homefeed = video_string.split("/")
        currentvideo_homefeed = currentvideo_homefeed == "1"
    else:
        # If the game has no away feed, the "video_string" variable will have
        # the following format: video_id/video_type
        # The home feed is selected automatically
        currentvideo_id, currentvideo_type = video_string.split("/")
        currentvideo_homefeed = 1

    # Get the video url. 
    # Authentication is needed over this point!
    currentvideo_url = getGameUrl(currentvideo_id, currentvideo_type, currentvideo_homefeed)
    if currentvideo_url:
        vars.cache.set("videourl_%s_%s_%d" % (currentvideo_type, currentvideo_id, currentvideo_homefeed), currentvideo_url)

        item = xbmcgui.ListItem(path=currentvideo_url)
        xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER).play(currentvideo_url, item)
    else:
        xbmc.executebuiltin('Notification(NBA League Pass,Video not found.,5000,)')

def gameHomeAwayMenu(video_string):
    currentvideo_id, currentvideo_type = video_string.split("/")

    # Create the "Home" and "Away" list items
    for ishomefeed in [True, False]:
        listitemname = "Away feed" if not ishomefeed else "Home feed"
        cached_url = vars.cache.get("videourl_%s_%s_%d" % (currentvideo_type, currentvideo_id, ishomefeed))
        if cached_url:
            addVideoListItem(listitemname, cached_url, "")
        else:
            url = "%s/%s/%d" % (currentvideo_id, currentvideo_type, ishomefeed)
            addListItem(listitemname, url, "playgame", "")

    xbmcplugin.endOfDirectory(handle = int(sys.argv[1]) )

def gameLinks(mode, url, date2Use = None):
    try:
        if mode == "selectdate":
            tday = getDate()
        elif mode == "oldseason":
            tday = date2Use
        else:
            tday = nowEST()
            log("current date (america timezone) is %s" % str(tday), xbmc.LOGDEBUG)

        # parse the video type
        video_type = url

        day = tday.isoweekday()
        # starts on mondays
        tday = tday - timedelta(day -1)
        now = tday
        default = "%04d/%d_%d" % (now.year, now.month, now.day)
        if mode in ["live", "thisweek", "selectdate", "oldseason"]:
            getGames(default, video_type)
        elif mode == "lastweek":
            tday = tday - timedelta(7)
            now = tday
            default = "%04d/%d_%d" % (now.year, now.month, now.day)
            getGames(default, video_type)
        else:
            getGames(default, video_type)

        # Can't sort the games list correctly because XBMC treats file items and directory
        # items differently and puts directory first, then file items (home/away feeds
        # require a directory item while only-home-feed games is a file item)
        #xbmcplugin.addSortMethod( handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    except:
        xbmcplugin.endOfDirectory(handle = int(sys.argv[1]),succeeded=False)
        return None

