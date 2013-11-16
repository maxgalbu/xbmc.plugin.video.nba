import json
import datetime, time
from datetime import date
from datetime import timedelta
import urllib,urllib2,httplib2
import xbmc,xbmcplugin,xbmcgui,xbmcaddon
from xml.dom.minidom import parseString
# import xpath # pip install py-dom-xpath
import re,os,binascii

try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

############################################################################
# global variables
settings = xbmcaddon.Addon( id="plugin.video.nba")
scores = settings.getSetting( id="scores")
debug = settings.getSetting( id="debug")

# map the quality_id to a video height
# Ex: 720p
quality_id = settings.getSetting( id="quality_id")
video_heights_per_quality = [720, 540, 432, 360]
target_video_height = video_heights_per_quality[int(quality_id)]
if debug:
    print "Chosen quality_id %s and target_video_height %d" % (quality_id, target_video_height)

cache = StorageServer.StorageServer("nbaleaguepass", 1)
cache.table_name = "nbaleaguepass"

# Delete the video urls cached if the video quality setting has changed
if cache.get("target_video_height") != str(target_video_height):
    cache.delete("video_%")
    cache.set("target_video_height", str(target_video_height))
    print "deleting video url cache"

cookies = ''
player_id = binascii.b2a_hex(os.urandom(16))
http = httplib2.Http()
media_dir = os.path.join(
    xbmc.translatePath("special://home/" ), 
    "addons", "plugin.video.nba"
    # "resources", "media"
)

# the default fanart image
fanart_image = os.path.join(media_dir, "fanart.jpg")
http.disable_ssl_certificate_validation=True
############################################################################

def isLiveUsable():
    # retrieve current installed version
    json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_query = json.loads(json_query)
    version_installed = []
    if json_query.has_key('result') and json_query['result'].has_key('version'):
        version_installed  = json_query['result']['version']
        print ("Version installed %s" %version_installed)

    return version_installed and version_installed['major'] >= 13

def getFeed():
    global fanart_image

    # get the feed url
    feed_url = "http://smb.cdnak.neulion.com/fs/nba/feeds/common/dl.js"
    req = urllib2.Request(feed_url, None);
    response = str(urllib2.urlopen(req).read())

    # Get the info from the feed
    # js.dl is an array with entries like this:
    #   {
    #   "geoAllow": "",
    #   "template": "",
    #   "id": 666,
    #   "subTitle": "",
    #   "title": "Pacers vs. Bulls",
    #   "description": "Derek Rose makes his long-awaited return",
    #   "link": "",
    #   "geoDeny": "",
    #   "game": {
    #     "id": "0011300002",
    #     "home": "IND",
    #     "status": 3,
    #     "gameDate": "2013-10-05T23:27:02.000",
    #     "visitor": "CHI"
    #   },
    #   "type": 1
    # }
    try:
        # Parse
        js = json.loads(response[response.find("{"):])
        dl = js["dl"]

        # for now only chose the first fanart
        first_id = dl[0]["id"]
        fanart_image = ("http://smb.cdnllnwnl.neulion.com/u/nba/nba/thumbs/dl/%s_pc.jpg" % first_id)
        settings.setSetting("fanart_image", fanart_image)
    except:
        print "Failed to parse the dl output!!!"
        return ''

def getDate( default= '', heading='Please enter date (YYYY/MM/DD)', hidden=False ):
    now = datetime.datetime.now()
    default = "%04d" % now.year + '/' + "%02d" % now.month + '/' + "%02d" % now.day
    keyboard = xbmc.Keyboard( default, heading, hidden )
    keyboard.doModal()
    ret = date.today()
    if ( keyboard.isConfirmed() ):
        sDate = unicode( keyboard.getText(), "utf-8" )
        temp = sDate.split("/")
        ret = date(int(temp[0]),  int(temp[1]), int(temp[2]))
    return ret

def login():
    try:
        # Login
        url = 'https://watch.nba.com/nba/secure/login?'
        body = {'username' : settings.getSetting( id="username"), 'password' : settings.getSetting( id="password")}
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        response_headers, content = http.request(url, 'POST', body=urllib.urlencode(body), headers=headers)        

        # If the response is not 200, it is not an authentication error
        global cookies
        if debug:
            print response_headers
        if response_headers["status"] != "200":
            if debug:
                print "Login failed with content: %s" % content
            xbmc.executebuiltin('Notification(NBA League Pass,Failed to login (response != 200),5000,)')
            return ''

        # Check the response xml
        xml = parseString(str(content))
        if xml.getElementsByTagName("code")[0].firstChild.nodeValue == "loginlocked":
            xbmc.executebuiltin('Notification(NBA League Pass,Cannot login: invalid username and password, or your account is locked.,5000,)')
        else:
            # logged in
            cookies = response_headers['set-cookie'].partition(';')[0]
        return cookies
    except:
        cookies = ''
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to login!,5000,)')
        return ''

def getGameUrl(video_id, video_type="archive"):
    # 
    # Make the first for the HLS manifest URL:
    # 
    global cookies
    global player_id
    global debug
    global target_video_height
    # addLink("video_type has value %s" % (video_type),'','','')

    if debug:
        print "cookies: %s %s" % (video_type, cookies)

    url = 'http://watch.nba.com/nba/servlets/publishpoint'
    headers = { 
        'Cookie': cookies, 
        'Content-type': 'application/x-www-form-urlencoded',
        'User-Agent': 'iPad' if video_type == "live" 
            else "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0",
    }
    body = { 
        'id': str(video_id), 
        'gt': video_type, 
        'type': 'game',
        'plid': player_id
    }
    if video_type != "live":
        body['isFlex'] = 'true'
    else:
        body['nt'] = '1'
    body = urllib.urlencode(body)

    response, content = http.request(url, 'POST', body=body, headers=headers)
    if response['status'] != "200":
        if debug:
            print str(content)
            print str(url)
            print "The content was %s" % str(content)
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to get a video URL. Are you logged in?,5000,)')
        return ''

    xml = parseString(str(content))
    link = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
    if debug:
        print link

    if video_type == "live":
        # transform the link
        match = re.search('http://([^:]+)/([^?]+?)\?(.+)$', link)
        domain = match.group(1)
        arguments = match.group(2)
        querystring = match.group(3)

        livecookies = "nlqptid=%s" % (querystring)
        livecookiesencoded = urllib.quote(livecookies)

        if debug:
            print "live cookie: %s %s" % (querystring, livecookies)

        full_video_url = "http://%s/%s?%s|Cookie=%s" % (domain, arguments, querystring, livecookiesencoded)
    else:
        # transform the link
        m = re.search('adaptive://([^/]+)(/[^?]+)\?(.+)$', link)
        domain = m.group(1)
        path = urllib.quote_plus(str(m.group(2)))
        arguments = m.group(3)
        http_link = "http://%s/play?url=%s&%s" % (domain, path, arguments)
        if debug:
            print http_link
        
        # Make the second request which will return video of a (now) hardcoded
        # quality 
        # NOTE: had to switch to urllib2, as httplib2 assumed that
        # because the port was 443 it should use SSL (although the protocol
        # was correctly set to http)
        try:
            opener = urllib2.build_opener()
            opener.addheaders.append(('Cookie', cookies))
            f = opener.open(http_link)
            content = f.read()
            f.close()
        except:
            content = ""
            pass
    
        if not content:
            if debug:
                print "no xml response, try guessing the url"
            full_video_url = getGameUrlGuessing(video_id, link)
        else:
            if debug:
                print "parsing xml response: %s" % content
            
            # parse the xml
            xml = parseString(str(content))
            all_streamdata = xml.getElementsByTagName("streamData")
            full_video_url = ''
            for streamdata in all_streamdata:
                video_height = streamdata.getElementsByTagName("video")[0].attributes["height"].value

                if int(video_height) == target_video_height:
                    selected_video_path = streamdata.attributes["url"].value
                    selected_domain = streamdata.getElementsByTagName("httpserver")[0].attributes["name"].value
                    full_video_url = getGameUrl_m3u8("http://%s%s" % (selected_domain, selected_video_path))

                    if urllib.urlopen(full_video_url).getcode() != 200:
                        full_video_url = ""
                    break
        
        if not full_video_url:
            if debug:
                print "parsed xml but video not found, try guessing the url"
            full_video_url = getGameUrlGuessing(video_id, link)
        
    if full_video_url and debug:
        print "the url of video %s is %s" % (video_id, full_video_url)

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
    target_bitrate = available_bitrates.get(target_video_height, 1600)
    failsafe_bitrate = available_bitrates.get(360)

    matches = re.search('adaptive://([^?]+)\?.+$', adaptive_link)
    video_url = matches.group(1)
    video_url = video_url.replace(":443", "")

    target_video_url = getGameUrlByBitrate(target_bitrate, video_url)
    target_video_url = getGameUrl_m3u8("http://%s" % target_video_url)

    if urllib.urlopen(target_video_url).getcode() != 200:
        if debug:
            print "video of height %d not found, trying with height 360" % target_video_height

        target_video_url = getGameUrlByBitrate(failsafe_bitrate, video_url)
        target_video_url = getGameUrl_m3u8("http://%s" % target_video_url)

        if urllib.urlopen(target_video_url).getcode() != 200:
            if debug:
                print "failsafe bitrate video not found, bailing out"
            return ""

    return target_video_url

def getGameUrlByBitrate(target_bitrate, video_url):
    # replace whole_1_pc\whole_2_pc with whole_[number]_[bitrate]
    return re.sub("whole_([0-9]+)_pc", "whole_\1_"+str(target_bitrate), video_url)

teams = {
    "bkn" : "Nets",
    "nyk" : "Knicks",
    "njn" : "Nets",
    "atl" : "Hawks",
    "was" : "Wizards",
    "phi" : "Sixers",
    "bos" : "Celtics",
    "chi" : "Bulls",
    "min" : "Timberwolves",
    "mil" : "Bucks",
    "cha" : "Bobcats",
    "dal" : "Mavericks",
    "lac" : "Clippers",
    "lal" : "Lakers",
    "sas" : "Spurs",
    "okc" : "Thunder",
    "noh" : "Hornets",
    "por" : "Blazers",
    "mem" : "Grizzlies",
    "mia" : "Heat",
    "orl" : "Magic",
    "sac" : "Kings",
    "tor" : "Raptors",
    "ind" : "Pacers",
    "det" : "Pistons",
    "cle" : "Cavaliers",
    "den" : "Nuggets",
    "uta" : "Jazz",
    "phx" : "Suns",
    "gsw" : "Warriors",
    "hou" : "Rockets",
    # non nba
    "fbu" : "Fenerbahce",
    "ubb" : "Bilbao",
    'mos' : "UCKA Moscow",
    'mac' : "Maccabi Haifa",
    'nop' : "New Orleans",
}

def getGames(fromDate = '', video_type = "archive"):
    global cache

    try:
        schedule = 'http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/' +fromDate +  '.js?t=' + "%d"  %time.time()
        print 'Requesting %s' % schedule
        # http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/2013/10_7.js?t=1381054350000
        req = urllib2.Request(schedule, None);
        response = str(urllib2.urlopen(req).read())
        js = json.loads(response[response.find("{"):])

        for game in js['games']:
            print game
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

                print v.lower()
                print h.lower()

                if game_id != '':
                    # Get pretty names for the team names
                    if v.lower() in teams:
                        visitor_name = teams[v.lower()]
                    else:
                        visitor_name = v
                    if h.lower() in teams:
                        host_name = teams[h.lower()]
                    else:
                        host_name = h

                    # Create the title
                    name = game_start_date_est[:10] + ' ' + visitor_name + ' vs ' + host_name
                    if scores == '1':
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
                        real_url = cache.get("videourl_%s_%s" % (video_type, game_id))
                        if real_url:
                            addVideoListItem(name, real_url, thumbnail_url)
                        else:
                            addListItem(name, url, video_mode, thumbnail_url)

    except Exception, e:
        xbmc.executebuiltin('Notification(NBA League Pass,'+str(e)+',5000,)')
        print str(e)
        pass

def playGame(video_string):
    # Authenticate
    global cookies, cache
    if cookies == '':
        cookies = login()

    # Decode the video string
    currentvideo_id, currentvideo_type = video_string.split("/")

    # Get the video url. 
    # Authentication is needed over this point!
    # addLink("getting the archive game video_id for game with id %s" % video_id,'','','')
    currentvideo_url = getGameUrl(currentvideo_id, currentvideo_type)
    if currentvideo_url:
        cache.set("videourl_%s_%s" % (currentvideo_type, currentvideo_id), currentvideo_url)

        item = xbmcgui.ListItem(path=currentvideo_url)
        xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER).play(currentvideo_url, item)
    else:
        xbmc.executebuiltin('Notification(NBA League Pass,Video not found.,5000,)')

def mainMenu():
    if isLiveUsable():
        addListItem('Live', 'live', 'live','', True)
    addListItem('Archive', 'archive', 'archive','', True)
    addListItem('Condensed', 'condensed', 'condensed','', True)
    # addListItem('Highlights', 'highlights', '1', '')

def dateMenu(type):
    addListItem('This week', type, 'thisweek' ,'', True)
    addListItem('Last week' , type, 'lastweek','', True)
    addListItem('Select date' , type, 'selectdate','', True)
    addListItem('2012-2013 season', type, 'oldseason','', True)

def liveMenu():
    gameLinks('', 'live')


def season2012(mode, url):
    # addLink("in season 2012",'','','')
    d1 = date(2012, 10, 30)
    week = 1
    while week < 36:
        # addLink("in week %s" % (d1),'','','')
        gameLinks(mode,url, d1)
        d1 = d1 + timedelta(7)
        week = week + 1

def gameLinks(mode, url, date2Use = None):
    try:
        if mode == "selectdate":
            tday = getDate()
        elif mode == "oldseason":
            tday = date2Use
        else:
            tday = date.today()

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

def getParams():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
    return param

def addVideoListItem(name,url,iconimage):
    return addListItem(name,url,"",iconimage,False,True)

def addListItem(name,url,mode,iconimage,isfolder=False,usefullurl=False):
    global fanart_image
    generated_url = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty('fanart_image', fanart_image)
    if not isfolder:
        liz.setProperty("IsPlayable", "true")
    if usefullurl:
        generated_url = url

    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=generated_url, listitem=liz, isFolder=isfolder)
    return liz

params=getParams()
url=None
mode=None

# Set the fanart image
s = settings.getSetting("fanart_image")
if s != '':
    fanart_image = s

try:
    url=urllib.unquote_plus(params["url"])
except:
    pass
try:
    mode=params["mode"]
except:
    pass

if mode == None or url == None or len(url)<1:
    # initialize the feed
    getFeed()

    # create the main menu
    mainMenu()
elif mode == "archive" or mode == "condensed":
    dateMenu(url)
elif mode == "playgame":
    playGame(url)
elif mode == "oldseason":
    season2012(mode, url)
elif mode == "live":
    liveMenu()
else:
    gameLinks(mode, url)


xbmcplugin.endOfDirectory(int(sys.argv[1]))
