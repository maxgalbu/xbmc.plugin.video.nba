import json,urllib2
import datetime, time
from datetime import timedelta
import xbmc,xbmcgui
import traceback
import calendar

from utils import *
from common import *
import vars

def addFavTeamGameLinks(fromDate, favTeamAbbrs, video_type = 'archive'):
    try:
        if type(fromDate) is datetime.datetime:
            fromDate = "%04d/%d_%d" % (fromDate.year, fromDate.month, fromDate.day)
        schedule = 'http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/' + fromDate +  '.js?t=' + "%d"  %time.time()
        log('Requesting %s' % schedule, xbmc.LOGDEBUG)

        now_datetime_est = nowEST()

        # http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/2013/10_7.js?t=1381054350000
        req = urllib2.Request(schedule, None);
        response = str(urllib2.urlopen(req).read())
        js = json.loads(response[response.find("{"):])

        unknown_teams = {}
        for game in reversed(js['games']):
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
                video_details = details.get('video', {})
                video_has_away_feed = video_details.get("af", False)

                # Try to convert start date to datetime
                try:
                    game_start_datetime_est = datetime.datetime.strptime(game_start_date_est, "%Y-%m-%dT%H:%M:%S.%f" )
                except:
                    game_start_datetime_est = datetime.datetime.fromtimestamp(time.mktime(time.strptime(game_start_date_est, "%Y-%m-%dT%H:%M:%S.%f")))

                #Set game start date in the past if python can't parse the date
                #so it doesn't get flagged as live or future game and you can still play it
                #if a video is available
                if type(game_start_datetime_est) is not datetime.datetime:
                    game_start_datetime_est = now_datetime_est + timedelta(-30)

                #guess end date by adding 4 hours to start date
                game_end_datetime_est = game_start_datetime_est + timedelta(hours=4)

                if game_id != '' and (v.lower() in favTeamAbbrs or h.lower() in favTeamAbbrs):
                    # Get pretty names for the team names
                    [visitor_name, host_name] = [vars.config['teams'].get(t.lower(), t) for t in [v, h]]
                    [unknown_teams.setdefault(t, []).append(game_start_datetime_est.strftime("%Y-%m-%d"))
                        for t in [v, h] if t.lower() not in vars.config['teams']]

                    has_video = "video" in details
                    future_video = game_start_datetime_est > now_datetime_est and \
                        game_start_datetime_est.date() == now_datetime_est.date()
                    live_video = game_start_datetime_est < now_datetime_est < game_end_datetime_est

                    # Create the title
                    name = game_start_datetime_est.strftime("%Y-%m-%d")
                    if video_type == "live":
                        name = toLocalTimezone(game_start_datetime_est).strftime("%Y-%m-%d (at %I:%M %p)")

                    # Add the teams' names and the scores if needed
                    name += ' %s vs %s' % (visitor_name, host_name)
                    if vars.show_scores and not future_video:
                        name += ' %s:%s' % (str(vs), str(hs))

                    thumbnail_url = generateCombinedThumbnail(v, h)

                    if video_type == "live":
                        if future_video:
                            name = "UPCOMING: " + name
                        elif live_video:
                            name = "LIVE: " + name

                    add_link = True
                    if video_type == "live" and not (live_video or future_video):
                        add_link = False
                    elif video_type != "live" and (live_video or future_video):
                        add_link = False
                    elif not future_video and not has_video:
                        add_link = False

                    if add_link == True:
                        awayFeed = video_has_away_feed and v.lower() in favTeamAbbrs
                        params = {
                            'video_id': game_id,
                            'video_type': video_type,
                            'video_ishomefeed': 0 if awayFeed else 1,
                            'game_state': gs
                        }
                        name = name + (' (away)' if awayFeed else ' (home)')

                        if 'st' in details:
                            start_time = calendar.timegm(time.strptime(details['st'], '%Y-%m-%dT%H:%M:%S.%f')) * 1000
                            params['start_time'] = start_time
                            if 'et' in details:
                                end_time = calendar.timegm(time.strptime(details['et'], '%Y-%m-%dT%H:%M:%S.%f')) * 1000
                                params['end_time'] = end_time
                                params['duration'] = end_time - start_time
                            else:
                                # create my own et for game (now)
                                end_time = str(datetime.datetime.now()).replace(' ', 'T')
                                end_time = calendar.timegm(time.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%f')) * 1000
                                params['end_time'] = end_time
                                params['duration'] = end_time - start_time
                                
                        addListItem(name, url="", mode="playgame", iconimage=thumbnail_url, customparams=params)

        if unknown_teams:
            log("Unknown teams: %s" % str(unknown_teams), xbmc.LOGWARNING)

    except Exception, e:
        xbmc.executebuiltin('Notification(NBA League Pass,'+str(e)+',5000,)')
        log(traceback.format_exc(), xbmc.LOGDEBUG)
        pass

def getCurrentMonday():
    tday = nowEST()
    return tday - timedelta(tday.isoweekday() - 1) # start on Monday

def favTeamMenu():
    updateFavTeam()

    if vars.fav_team_abbrs is None:
        xbmcgui.Dialog().ok(vars.__addon_name__, 'Set your favorite team in the settings')
        xbmcaddon.Addon().openSettings()
        updateFavTeam()
        if vars.fav_team_abbrs is None:
            addListItem('Set your favorite team in the settings', '', 'favteam', '', False)
            return

    log("Loading games for: %s" % str(vars.fav_team_abbrs))
    tday = getCurrentMonday()
    addFavTeamGameLinks(tday, vars.fav_team_abbrs, 'live')
    weeksBack = 0
    while monthIsInSeason(tday.month) and weeksBack < 3:
        addFavTeamGameLinks(tday, vars.fav_team_abbrs)
        tday = tday - timedelta(7)
        weeksBack = weeksBack + 1

    if tday.month >= 10:
        addListItem('Older games', 'older', 'favteam', '', True)

def favTeamOlderMenu():
    updateFavTeam()
    
    log("Loading older games for: %s" % str(vars.fav_team_abbrs))
    tday = getCurrentMonday() - timedelta(14)
    while monthIsInSeason(tday.month):
        addFavTeamGameLinks(tday, vars.fav_team_abbrs)
        tday = tday - timedelta(7)

def monthIsInSeason(month):
    return month >= 10 or month <= 6
