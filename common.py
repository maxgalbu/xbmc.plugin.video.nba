import json
import datetime
import urllib,urllib2
import xbmc,xbmcplugin,xbmcgui
from xml.dom.minidom import parseString

import vars
from utils import *

def getFanartImage():
    # get the feed url
    feed_url = "http://smb.cdnak.neulion.com/fs/nba/feeds/common/dl.js"
    req = urllib2.Request(feed_url, None);
    response = str(urllib2.urlopen(req).read())
    
    try:
        # Parse
        js = json.loads(response[response.find("{"):])
        dl = js["dl"]

        # for now only chose the first fanart
        first_id = dl[0]["id"]
        fanart_image = ("http://smb.cdnllnwnl.neulion.com/u/nba/nba/thumbs/dl/%s_pc.jpg" % first_id)
        vars.settings.setSetting("fanart_image", fanart_image)
    except:
        print "Failed to parse the dl output!!!"
        return ''

def getDate( default= '', heading='Please enter date (YYYY/MM/DD)', hidden=False ):
    now = datetime.datetime.now()
    default = "%04d" % now.year + '/' + "%02d" % now.month + '/' + "%02d" % now.day
    keyboard = xbmc.Keyboard( default, heading, hidden )
    keyboard.doModal()
    ret = datetime.date.today()
    if ( keyboard.isConfirmed() ):
        sDate = unicode( keyboard.getText(), "utf-8" )
        temp = sDate.split("/")
        ret = datetime.date(int(temp[0]),  int(temp[1]), int(temp[2]))
    return ret

def login():
    try:
        # Login
        url = 'https://watch.nba.com/nba/secure/login?'
        body = {'username': vars.settings.getSetting( id="username"), 'password': vars.settings.getSetting( id="password")}
        body = urllib.urlencode(body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            request = urllib2.Request(url, body, headers)
            response = urllib2.urlopen(request)
            content = response.read()
        except urllib2.HTTPError as e:
            log("Login failed with code: %d and content: %s" % (e.getcode(), e.read()))
            xbmc.executebuiltin('Notification(NBA League Pass,Failed to login (response != 200),5000,)')
            return ''

        # Check the response xml
        xml = parseString(str(content))
        if xml.getElementsByTagName("code")[0].firstChild.nodeValue == "loginlocked":
            xbmc.executebuiltin('Notification(NBA League Pass,Cannot login: invalid username and password, or your account is locked.,5000,)')
        else:
            # logged in
            vars.cookies = response.info().getheader('Set-Cookie').partition(';')[0]
        return vars.cookies
    except:
        vars.cookies = ''
        xbmc.executebuiltin('Notification(NBA League Pass,Failed to login!,5000,)')
        return ''
