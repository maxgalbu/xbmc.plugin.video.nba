import xbmc,xbmcplugin,xbmcgui,xbmcaddon,xbmcvfs
import urllib,urllib2,urlparse,datetime,json,sys,pytz
import os
from dateutil.tz import tzlocal
from PIL import Image,ImageOps

import vars

def littleErrorPopup(error, seconds=5000):
    xbmc.executebuiltin('Notification(NBA League Pass,%s,%d,)' % (error, seconds))

def logHttpException(exception, url, body=""):
    log_string = ""
    if hasattr(exception, 'reason'):
        log_string = "Failed to get video url: %s. The url was %s" % (exception.reason, url)
    elif hasattr(exception, 'code'):
        log_string = "Failed to get video url: code %d. The url was %s" % (exception.code, url)
    else:
        log_string = "Failed to get video url. The url was %s" % (url)

    log(body)
    if body != "":
        log_string += " - The body was: %s" % body

    log(log_string)

#Get the current date and time in EST timezone
def nowEST():
    if hasattr(nowEST, "datetime"):
        return nowEST.datetime

    #Convert UTC to EST datetime
    timezone = pytz.timezone('America/New_York')
    utc_datetime = datetime.datetime.utcnow()
    est_datetime = utc_datetime + timezone.utcoffset(utc_datetime)
    log("UTC datetime: %s" % utc_datetime)
    log("EST datetime: %s" % est_datetime)

    #Save the result to a static variable
    nowEST.datetime = est_datetime

    return est_datetime

#Returns a datetime in the local timezone
#Thanks: http://stackoverflow.com/a/8328904/2265500
def toLocalTimezone(date):
    #Check settings
    if not vars.use_local_timezone:
        return date

    #Pick the first timezone name found
    local_timezone = tzlocal()

    #Get the NBA league pass timezone (EST)
    est_timezone = pytz.timezone('America/New_York')

    #Localize the date to include the offset, then convert to local timezone
    return est_timezone.localize(date).astimezone(local_timezone)

def isLiveUsable():
    # retrieve current installed version
    json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_query = json.loads(json_query)
    version_installed = []
    if json_query.has_key('result') and json_query['result'].has_key('version'):
        version_installed  = json_query['result']['version']
        log("Version installed %s" %version_installed, xbmc.LOGDEBUG)

    return version_installed and version_installed['major'] >= 13

def log(txt, severity=xbmc.LOGINFO):
    if severity == xbmc.LOGDEBUG and not vars.debug:
        pass
    else:
        try:
            message = ('##### %s: %s' % (vars.__addon_name__,txt) )
            xbmc.log(msg=message, level=severity)
        except UnicodeEncodeError:
            message = ('##### %s: UnicodeEncodeError' %vars.__addon_name__)
            xbmc.log(msg=message, level=xbmc.LOGWARNING)

def getParams():
    params = {}
    paramstring = sys.argv[2]
    paramstring = paramstring.replace('?','')
    if len(paramstring) > 0:
        if paramstring[len(paramstring)-1] == '/':
            paramstring = paramstring[0:len(paramstring)-2]

        params = urlparse.parse_qsl(paramstring)
        params = dict(params)
    return params

def addVideoListItem(name, url, iconimage):
    return addListItem(name,url,"",iconimage,False,True)

def addListItem(name, url, mode, iconimage, isfolder=False, usefullurl=False, customparams={}):
    if not hasattr(addListItem, "fanart_image"):
        settings = xbmcaddon.Addon( id=vars.__addon_id__)
        addListItem.fanart_image = settings.getSetting("fanart_image")

    params = {
        'url': url,
        'mode': str(mode),
        'name': name
    }

    #merge params with customparams
    params.update(customparams)

    #Fix problems of encoding with urlencode and utf8 chars
    for key, value in params.iteritems():
        params[key] = unicode(value).encode('utf-8')

    #urlencode the params
    params = urllib.urlencode(params)

    generated_url = "%s?%s" % (sys.argv[0], params)
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )

    if addListItem.fanart_image:
        liz.setArt({
            "fanart": addListItem.fanart_image
        })

    if not isfolder:
        liz.setProperty("IsPlayable", "true")
    if usefullurl:
        generated_url = url

    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=generated_url, listitem=liz, isFolder=isfolder)
    return liz

def prepareSingleThumbnail(im, width, height):
    im_components = im.split()
    if len(im_components) == 4:
        im_temp = Image.new('RGBA', im.size)
        im_temp.paste(im, mask=im_components[3])

        # Crop if possible
        if im.getbbox() != im_temp.getbbox():
            im = im.crop(im_temp.getbbox())

    # Achieve ratio width : height
    im_temp = None
    if im.size[0] * height > im.size[1] * width: # Pad to height
        im_temp = Image.new('RGBA', (im.size[0], im.size[0] * height / width))
    else: # Pad to width
        im_temp = Image.new('RGBA', (im.size[1] * width / height, im.size[1]))
    im_temp.paste(im, ((im_temp.size[0] - im.size[0]) / 2, (im_temp.size[1] - im.size[1]) / 2), im)

    # Resize to fit (width, height)
    im = ImageOps.fit(im_temp, (width, height), Image.ANTIALIAS)
    return im

def generateCombinedThumbnail(v, h, width=2*500, height=500, padding=10, load_if_exists=True):
    combined_thumbnail_path = os.path.join(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode("utf-8"), "thumbnails")
    if not xbmcvfs.exists(combined_thumbnail_path):
        xbmcvfs.mkdir(combined_thumbnail_path)
    combined_thumbnail_fullname = os.path.join(combined_thumbnail_path, ("%s-%s.png" % (v.lower(), h.lower())))
    if load_if_exists and os.path.isfile(combined_thumbnail_fullname):
        return combined_thumbnail_fullname

    SINGLE_THUMBNAIL_URL_MASK = "http://i.cdn.turner.com/nba/nba/.element/img/1.0/teamsites/logos/teamlogos_500x500/%s.png"
    [im_v, im_h] = [Image.open(urllib2.urlopen(SINGLE_THUMBNAIL_URL_MASK % t.lower())).convert('RGBA') for t in [v, h]]
    [im_v, im_h] = [prepareSingleThumbnail(im, width / 2 - 2 * padding, height - 2 * padding) for im in [im_v, im_h]]

    im_combined = Image.new('RGBA', (width, height))
    im_combined.paste(im_v, (padding, padding), im_v)
    im_combined.paste(im_h, (width / 2 + padding, padding), im_h)
    im_combined.save(combined_thumbnail_fullname)
    return combined_thumbnail_fullname
