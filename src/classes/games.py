from datetime import timedelta
import xbmc,xbmcplugin,xbmcgui
import re,urllib

from common import *
from request import Request
from schedule import Schedule
import vars


class Games:
    @staticmethod
    def getGameUrl(video_id, video_type, video_ishomefeed):
        log("cookies: %s %s" % (video_type, vars.cookies), xbmc.LOGDEBUG)

        # video_type could be archive, live, condensed or oldseason
        if video_type not in ["live", "archive", "condensed"]:
            video_type = "archive"

        gt = 1
        if not video_ishomefeed:
            gt = 4
        if video_type == "condensed":
            gt = 8

        url = vars.config['publish_endpoint']
        headers = {
            'Cookie': vars.cookies,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'iPad' if video_type == "live"
            else "AppleCoreMedia/1.0.0.8C148a (iPad; U; CPU OS 6_2_1 like Mac OS X; en_us)",
        }
        body = {
            'extid': str(video_id),
            'format': "xml",
            'gt': gt,
            'gs': vars.params.get("game_state", "3"),
            'type': 'game',
            'plid': vars.player_id,
        }
        if vars.params.get("camera_number"):
            body['cam'] = vars.params.get("camera_number")
        if video_type != "live":
            body['format'] = 'xml'

        log("the body of publishpoint request is: %s" % urllib.urlencode(body), xbmc.LOGDEBUG)

        xml = Request.getXml(url, body, headers)
        url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue

        selected_video_url = ''
        if video_type == "live":
            # transform the url
            match = re.search('http://([^:]+)/([^?]+?)\?(.+)$', url)
            domain = match.group(1)
            arguments = match.group(2)
            querystring = match.group(3)

            livecookies = "nlqptid=%s" % (querystring)
            livecookiesencoded = urllib.quote(livecookies)

            log("live cookie: %s %s" % (querystring, livecookies), xbmc.LOGDEBUG)

            url = "http://%s/%s?%s" % (domain, arguments, querystring)
            url = getGameUrlWithBitrate(url, video_type)

            selected_video_url = "%s|Cookie=%s" % (url, livecookiesencoded)
        else:
            # Archive and condensed flow: We now work with HLS.
            # The cookies are already in the URL and the server will supply them to ffmpeg later.
            selected_video_url = getGameUrlWithBitrate(url, video_type)

        if selected_video_url:
            log("the url of video %s is %s" % (video_id, selected_video_url), xbmc.LOGDEBUG)

        return selected_video_url

    @staticmethod
    def addGamesLinks(date, video_type = "archive"):
        schedule = Schedule()
        games = schedule.getGames(date)

        for game in games:
            add_link = True
            if video_type == "live" and not (game['is_live_video'] or game['is_future_video']):
                add_link = False
            elif video_type != "live" and (game['is_live_video'] or game['is_future_video']):
                add_link = False
            elif not game['is_future_video'] and not game['has_video']:
                add_link = False

            if add_link:
                params = {
                    'video_id': game['video_id'],
                    'video_type': video_type,
                    'seo_name': game['seo_name'],
                    'has_away_feed': game['has_away_feed'],
                    'has_condensed_video': game['has_condensed_video'],
                }

                # Add a directory item that contains home/away/condensed items
                addListItem(game['name'], url="", mode="gamechoosevideo",
                    iconimage=game['thumbnail_url'], isfolder=True, customparams=params)

    @staticmethod
    def getHighlightGameUrl(video_id):
        url = 'https://watch.nba.com/service/publishpoint'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': "AppleCoreMedia/1.0.0.8C148a (iPad; U; CPU OS 6_2_1 like Mac OS X; en_us)",
        }
        
        body = {
            'extid': str(video_id),
            'plid': vars.player_id,
            'gt': "64",
            'type': 'game',
            'bitrate': "1600"
        }

        log("the body of publishpoint request is: %s" % urllib.urlencode(body), xbmc.LOGDEBUG)

        xml = Request.getXml(url, body, headers)
        if not xml:
            log("Highlight url not found.", xbmc.LOGERROR)
            return ''

        url = xml.getElementsByTagName("path")[0].childNodes[0].nodeValue

        # Remove everything after ? otherwise XBMC fails to read the rtpm stream
        url, _,_ = url.partition("?")

        log("highlight video url: %s" % url, xbmc.LOGDEBUG)
        
        return url

    @staticmethod
    def playGame():
        # Authenticate
        if vars.cookies == '':
            vars.cookies = login()
        if not vars.cookies:
            return

        currentvideo_id = vars.params.get("video_id")
        currentvideo_type  = vars.params.get("video_type")
        currentvideo_ishomefeed = vars.params.get("video_ishomefeed", "1")
        currentvideo_ishomefeed = currentvideo_ishomefeed == "1"

        # Get the video url. 
        # Authentication is needed over this point!
        currentvideo_url = Games.getGameUrl(currentvideo_id, currentvideo_type, currentvideo_ishomefeed)
        if currentvideo_url:
            item = xbmcgui.ListItem(path=currentvideo_url)
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)

    @staticmethod
    def chooseGameVideoMenu():
        video_id = vars.params.get("video_id")
        video_type = vars.params.get("video_type")
        seo_name = vars.params.get("seo_name")
        has_away_feed = vars.params.get("has_away_feed", "0") == "1"
        has_condensed_video = vars.params.get("has_condensed_video", "0") == "1"

        game_data_json = Request.getJson(vars.config['game_data_endpoint'] % seo_name)
        game_state = game_data_json['gameState']
        game_cameras = []
        if 'multiCameras' in game_data_json:
            game_cameras = game_data_json['multiCameras'].split(",")

        nba_config = Request.getJson(vars.config['config_endpoint'])
        nba_cameras = {}
        for camera in nba_config['content']['cameras']:
            nba_cameras[ camera['number'] ] = camera['name']

        if has_away_feed:
            # Create the "Home" and "Away" list items
            for ishomefeed in [True, False]:
                listitemname = "Full game, " + ("away feed" if not ishomefeed else "home feed")
                params = {
                    'video_id': video_id,
                    'video_type': video_type,
                    'video_ishomefeed': 1 if ishomefeed else 0,
                    'game_state': game_state
                }

                thumbnail_url = vars.config['thumbnail_url'] % \
                    game_data_json[ 'homeTeam' if ishomefeed else 'awayTeam' ]['code'].lower()

                addListItem(listitemname, url="", mode="playgame", iconimage=thumbnail_url, customparams=params)
        else:
            # Add a "Home" list item
            params = {
                'video_id': video_id,
                'video_type': video_type,
                'game_state': game_state
            }

            thumbnail_url = vars.config['thumbnail_url'] % \
                game_data_json['homeTeam']['code'].lower()

            addListItem("Full game", url="", mode="playgame", iconimage=thumbnail_url, customparams=params)

        # Add all the cameras available
        for camera_number in game_cameras:
            # Skip camera number 0 (broadcast?) - the full game links are the same
            camera_number = int(camera_number)
            if camera_number == 0:
                continue

            params = {
                'video_id': video_id,
                'video_type': video_type,
                'game_state': game_state,
                'camera_number': camera_number
            }

            name = "Camera %d: %s" % (camera_number, nba_cameras[camera_number])
            addListItem(name, url="", mode="playgame", iconimage="", customparams=params)

        # Live games have no condensed or highlight link
        if video_type != "live":
            # Create the "Condensed" list item
            if has_condensed_video:
                params = {
                    'video_id': video_id,
                    'video_type': 'condensed',
                    'game_state': game_state
                }
                addListItem("Condensed game", url="", mode="playgame", iconimage="", customparams=params)

            # Get the highlights video if available
            highlights_url = Games.getHighlightGameUrl(video_id)
            if highlights_url:
                addVideoListItem("Highlights", highlights_url, iconimage="")

        xbmcplugin.endOfDirectory(handle = int(sys.argv[1]) )

    @staticmethod
    def chooseGameMenu(mode, video_type, date2Use = None):
        if mode == "selectdate":
            date = getDate()
        elif mode == "oldseason":
            date = date2Use
        else:
            date = nowEST()
            log("current date (america timezone) is %s" % str(date), xbmc.LOGDEBUG)
        
        # starts on mondays
        day = date.isoweekday()
        date = date - timedelta(day-1)
        if mode == "lastweek":
            date = date - timedelta(7)
            
        Games.addGamesLinks(date, video_type)

        # Can't sort the games list correctly because XBMC treats file items and directory
        # items differently and puts directory first, then file items (home/away feeds
        # require a directory item while only-home-feed games is a file item)
        #xbmcplugin.addSortMethod( handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_DATE )
