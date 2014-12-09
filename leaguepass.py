import datetime, time
from datetime import date
from datetime import timedelta
import urllib
import xbmc,xbmcplugin,xbmcgui,xbmcaddon
import sys

from utils import *
from games import *
from common import *
from videos import *
from nbatvlive import *
import vars

log("Chosen quality_id %s and target_video_height %d" % (vars.quality_id, vars.target_video_height))

def mainMenu():
    if isLiveUsable():
        addListItem('Live', 'live', 'live','', True)
    addListItem('Archive', 'archive', 'archive','', True)
    addListItem('Condensed', 'condensed', 'condensed','', True)
    if isLiveUsable():
        addListItem('NBA TV Live', '', 'nbatvlive','')
    addListItem('Highlights', '', 'videohighlights','', True)
    addListItem('Top Plays', '', 'videotopplays','', True)

def dateMenu(type):
    addListItem('This week', type, 'thisweek' ,'', True)
    addListItem('Last week' , type, 'lastweek','', True)
    addListItem('Select date' , type, 'selectdate','', True)

    # Dynamic previous season, so I don't have to update this every time!
    now = date.today()
    current_year = now.year
    if now.month <= 10: #October
        current_year -= 1
    addListItem('%d-%d season' % (current_year-1, current_year), type, 'oldseason', '', True)

def liveMenu():
    gameLinks('', 'live')


def season2012(mode, url):
    # addLink("in season 2012",'','','')
    d1 = date(2012, 10, 30)
    week = 1
    while week < 36:
        # addLink("in week %s" % (d1),'','','')
        gameLinks(mode, url, d1)
        d1 = d1 + timedelta(7)
        week = week + 1

params=getParams()
url=None
mode=None

try:
    url=urllib.unquote_plus(params["url"])
except:
    pass
try:
    mode=params["mode"]
except:
    pass

if mode == None:
    getFanartImage()
    mainMenu()
elif mode == "archive" or mode == "condensed":
    dateMenu(url)
elif mode == "playgame":
    playGame(url)
elif mode == "gamehomeaway":
    gameHomeAwayMenu(url)
elif mode == "oldseason":
    season2012(mode, url)
elif mode == "live":
    liveMenu()
elif mode.startswith("video"):
    if mode.startswith("videoplay"):
        videoPlay(url)
    elif mode.startswith("videodate"):
        videoMenu(url, mode.replace("videodate", "") )
    else:
        videoDateMenu( mode.replace("video", "") )
elif mode == "nbatvlive":
    playLiveTV()
else:
    gameLinks(mode, url)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
