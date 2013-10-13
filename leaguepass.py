import json
import datetime, time
from datetime import date
from datetime import timedelta
import urllib,urllib2,re,time,xbmcplugin,xbmcgui, xbmcaddon, os, httplib2
from xml.dom.minidom import parse, parseString
import xpath # pip install py-dom-xpath
import re
import os,binascii

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

cookies = ''
player_id = binascii.b2a_hex(os.urandom(16))
http = httplib2.Http()
media_dir = os.path.join(
    xbmc.translatePath("special://home/" ), 
    "addons", "plugin.video.nba",
    "resources", "media"
)

# the default fanart image
fanart_image = os.path.join(media_dir, "fanart1.jpg")
http.disable_ssl_certificate_validation=True
############################################################################

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
        url = 'https://watch.nba.com/nba/secure/login?'
        body = {'username' : settings.getSetting( id="username"), 'password' : settings.getSetting( id="password")}
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        response, content = http.request(url+urllib.urlencode(body), 'POST', headers=headers)
        global cookies
        cookies  = response['set-cookie'].partition(';')[0]
        return cookies
    except:
        return ''

def get_game_url(video_id, video_type="archive"):
    try:
        # 
        # Make the first for the HLS manifest URL:
        # 
        global cookies
        global player_id
        global debug
        global target_video_height
        # addLink("video_type has value %s" % (video_type),'','','')

        url = 'http://watch.nba.com/nba/servlets/publishpoint'
        headers = { 
            'Cookie': cookies , 
            'Content-type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0',
        }
        body = urllib.urlencode({ 
            'id': str(video_id), 
            'isFlex': 'true',
            'gt': video_type, 
            'type': 'game',
            'plid': player_id
        })
        response, content = http.request(url, 'POST', body=body, headers=headers)
        if response['status'] != "200":
            print str(content)
            print str(url)
            addLink("returning because return code wasn't 200. The content was %s" % str(content),'','','')
            return ''
        xml = parseString(str(content))
        link = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue
        if debug:
            print link

        # transform the link
        m = re.search('adaptive://([^/]+)(.+)$', link)
        arguments = urllib.quote_plus(str(m.group(2)))
        domain = m.group(1)
        http_link = "http://%s/play?url=%s" % (domain, arguments)
        if debug:
            print http_link


        # Make the second request which will return video of a (now) hardcoded
        # quality 
        # NOTE: had to switch to urllib2, as httplib2 assumed that
        # because the port was 443 it should use SSL (although the protocol
        # was correctly set to http)
        opener = urllib2.build_opener()
        opener.addheaders.append(('Cookie', cookies))
        f = opener.open(http_link)
        content = f.read()
        f.close()

        # parse the xml
        xml = parseString(str(content))
        all_streamdata = xml.getElementsByTagName("streamData")
        full_video_url = ''
        for streamdata in all_streamdata:
            video_height = streamdata.getElementsByTagName("video")[0].attributes["height"].value

            if int(video_height) == target_video_height:
                selected_video_path = streamdata.attributes["url"].value
                selected_domain = streamdata.getElementsByTagName("httpserver")[0].attributes["name"].value
                full_video_url = "http://%s%s" % (selected_domain, selected_video_path)
                break

        # A HACK: HLS will be more bandwidth efficient
        m3u8_url = re.sub(r'\.mp4$', ".mp4.m3u8", full_video_url)
        if debug:
            print "the url of video %s is %s" % (video_id, m3u8_url)
        return m3u8_url
    except:
        # raise
        return 'ERROR!'

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
    try:
        date = ''
        h = ''
        v = ''
        gid =''
        st = ''
        vs = ''
        hs = ''
        idx = ''
        t = ''
        s = ''
        thisweek = 'http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/' +fromDate +  '.js?t=' + "%d"  %time.time()
        print 'Requesting ', thisweek
        # http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/2013/10_7.js?t=1381054350000
        req = urllib2.Request(thisweek, None);
        response = str(urllib2.urlopen(req).read())
        print response
        js = json.loads(response[response.find("{"):])
        print js

        for game in js['games']:
            print game
            for details in game:
                print details
                try:
                    h = details['h']
                    v = details['v']
                    gid = details['id']
                    date = details['d']
                    try:
                        st = details['st']
                        vs = str(details['vs'])
                        hs = str(details['hs'])
                    except:
                        vs = ''
                        hs = ''
                except  Exception, e:
                    # continue
                    raise
                print v.lower()
                print h.lower()
                if gid != '':
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
                    name = date[:10] + ' ' + visitor_name + ' vs ' + host_name
                    if scores == '1':
                        name = name + ' ' + vs + ':' + hs
                    # print name, date
                    thumbnail_url = ("http://e1.cdnl3.neulion.com/nba/player-v4/nba/images/teams/%s.png" % h)
                    # print thumbnail_url
                    addDir(name, "%s/%s" % (gid, video_type), '5', thumbnail_url)
    except:
        # raise
        print "Error!!!"
        return None

def playGame(title, video_string):
    # Authenticate
    global cookies
    if cookies == '':
        cookies  = login()

    # Decode the video string
    video_id, video_type = video_string.split("/")

    # Get the video url. 
    # Authentication is needed over this point!
    # addLink("getting the archive game video_id for game with id %s" % video_id,'','','')
    link = get_game_url(video_id, video_type)
    if link != '':
        addLink(title, link, '', '')
        liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage='')
        liz.setInfo( type="Video", infoLabels={ "Title": title } )
        xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER).play(link,liz)

def mainMenu():
    addDir('Archive', 'archive', '1','')
    addDir('Condensed', 'condensed', '1','')
    # addDir('Highlights', 'highlights', '1', '')

def dateMenu(type):
    addDir('This week',  type, '2' ,'')
    addDir('Last week' , type, '3','')
    addDir('Select date' , type, '4','')
    addDir('2012-2013 season', type, '6','')

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
        if mode == 4:
            tday = getDate()
        elif mode == 6:
            tday = date2Use
        else:
            tday = date.today()

        # parse the video type
        video_type = url

        day = tday.isoweekday()
        # starts on mondays
        tday = tday - timedelta(day -1)
        now = tday
        default = "%04d" % now.year
        default = default + '/' + "%d" % now.month
        default = default + '_' + "%d" % now.day
        if mode == 2 or mode ==4 or mode ==6:
            # addLink("asked to get games for %s %s" % (default, video_type),'','','')
            # print "Calling getGames with %s %s" %(default, video_type)
            getGames(default, video_type)
        elif mode == 3:
            tday = tday - timedelta(7)
            now = tday
            default = "%04d" % now.year
            default = default + '/' + "%d" % now.month
            default = default + '_' + "%d" % now.day
            getGames(default, video_type)
        else:
            getGames(default, video_type)
        xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
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

def addLink(name,url,title,iconimage):
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": title } )
    global fanart_image
    liz.setProperty('fanart_image', fanart_image)
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)

def addDir(name,url,mode,iconimage):
    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    global fanart_image
    liz.setProperty('fanart_image', fanart_image)
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)

params=getParams()
url=None
name=None
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
    name=urllib.unquote_plus(params["name"])
except:
    pass
try:
    mode=int(params["mode"])
except:
    pass

if mode==None or url==None or len(url)<1:
    # initialize the feed
    getFeed()

    # create the main menu
    mainMenu()

elif mode==1:
    dateMenu(url)

elif mode==5:
    playGame(name, url)
elif mode==6:
    season2012(mode, url)
else:
    gameLinks(mode, url)


xbmcplugin.endOfDirectory(int(sys.argv[1]))
