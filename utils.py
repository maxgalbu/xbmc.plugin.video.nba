import xbmc,xbmcplugin,xbmcgui,xbmcaddon
import urllib, datetime, json, sys

import vars

def nowEST():
    return datetime.datetime.utcnow() - datetime.timedelta(hours=5)

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
    param={}
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

def addVideoListItem(name, url, iconimage):
    return addListItem(name,url,"",iconimage,False,True)

def addListItem(name, url, mode, iconimage, isfolder=False, usefullurl=False, customparams={}):
    if not hasattr(addListItem, "fanart_image"):
        settings = xbmcaddon.Addon( id="plugin.video.nba")
        addListItem.fanart_image = settings.getSetting("fanart_image")

    params = {
        'url': url,
        'mode': str(mode),
        'name': name
    }
    params.update(customparams) #merge params with customparams
    params = urllib.urlencode(params) #urlencode the params

    generated_url = "%s?%s" % (sys.argv[0], params)
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )

    if addListItem.fanart_image:
        liz.setProperty('fanart_image', addListItem.fanart_image)

    if not isfolder:
        liz.setProperty("IsPlayable", "true")
    if usefullurl:
        generated_url = url

    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=generated_url, listitem=liz, isFolder=isfolder)
    return liz
