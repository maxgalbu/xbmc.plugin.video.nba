from datetime import timedelta
import xbmc,xbmcgui,xbmcaddon
import traceback

from common import *
from schedule import Schedule
import utils
import vars


class FavTeam:
    @staticmethod
    def updateFavTeam():
        vars.fav_team = None

        settings = xbmcaddon.Addon(id=vars.__addon_id__)
        fav_team_name = settings.getSetting( id="fav_team")
        if fav_team_name:
            for abbr, name in vars.config['teams'].items():
                if fav_team_name == name:
                    vars.fav_team = abbr
                    xbmc.log(msg="fav_team set to %s" % vars.fav_team, level=xbmc.LOGWARNING)

    @staticmethod
    def addGameLinks(date, fav_team, video_type='archive'):
        try:
            schedule = Schedule()
            games = schedule.getGames(date)

            # Reversed order (newer games first)
            for game in reversed(games):
                if fav_team not in [game['visitor_name'].lower(), game['host_name'].lower()]:
                    continue

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

                        # Play the away feed if the favorite team is away and there's an away feed
                        'video_ishomefeed': 0 if game['has_away_feed'] and fav_team == game['visitor_name'] else 1
                    }
                    name = game['name'] + (' (away)' if fav_team == game['visitor_name'] else ' (home)')

                    addListItem(name, url="", mode="playgame", iconimage="", customparams=params)

        except Exception, e:
            utils.littleErrorPopup(str(e))
            log(traceback.format_exc(), xbmc.LOGDEBUG)
            pass

    @staticmethod
    def getCurrentMonday():
        monday = nowEST()
        return monday - timedelta(monday.isoweekday() - 1)  # start on Monday

    @staticmethod
    def menu():
        FavTeam.updateFavTeam()

        if vars.fav_team is None:
            xbmcgui.Dialog().ok(vars.__addon_name__, 'Set your favourite team in the settings')
            xbmcaddon.Addon().openSettings()
            FavTeam.updateFavTeam()
            if vars.fav_team is None:
                addListItem('Set your favourite team in the settings', '', 'favteam', '', False)
                return

        log("Loading games for: " + vars.fav_team)
        monday = FavTeam.getCurrentMonday()

        FavTeam.addGameLinks(monday, vars.fav_team, 'live')
        weeksBack = 0
        while FavTeam.monthIsInSeason(monday.month) and weeksBack < 3:
            FavTeam.addGameLinks(monday, vars.fav_team)
            monday = monday - timedelta(7)
            weeksBack += 1

        if monday.month >= 10:
            addListItem('Older games', 'older', 'favteam', '', True)

    @staticmethod
    def olderMenu():
        FavTeam.updateFavTeam()
        
        log("Loading older games for: " + vars.fav_team)
        monday = FavTeam.getCurrentMonday() - timedelta(14)
        while FavTeam.monthIsInSeason(monday.month):
            FavTeam.addGameLinks(monday, vars.fav_team)
            monday = monday - timedelta(7)

    @staticmethod
    def monthIsInSeason(month):
        return month >= 10 or month <= 6
