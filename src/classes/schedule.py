import datetime, time
from datetime import timedelta
import xbmc
import traceback

from common import * 
from request import Request
import vars
import utils


class Schedule:
    def __init__(self):
        now = datetime.datetime.now()
        self.playoff_json = self.downloadPlayoffJson(now.year)

    def getGames(self, date):
        games = []

        try:
            now_datetime_est = utils.nowEST()

            #example: http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/2013/10_7.js?t=1381054350000
            schedule = 'http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/%04d/%d_%d.js?t=%d' % \
                (date.year, date.month, date.day, time.time())
            schedule_json = Request.getJson(schedule)

            for daily_games in schedule_json['games']:
                for game in daily_games:
                    h = game.get('h', '')
                    v = game.get('v', '')
                    game_id = game.get('id', '')
                    game_start_date_est = game.get('d', '')
                    vs = game.get('vs', '')
                    hs = game.get('hs', '')
                    seo_name = game.get("seoName", "")
                    has_condensed_video = game.get("video", {}).get("c", False)

                    video_details = game.get('video', {})
                    has_away_feed = bool(video_details.get("af", {}))

                    # Try to convert start date to datetime
                    try:
                        game_start_datetime_est = datetime.datetime.strptime(game_start_date_est, "%Y-%m-%dT%H:%M:%S.%f" )
                    except:
                        game_start_datetime_est = datetime.datetime.fromtimestamp(time.mktime(time.strptime(game_start_date_est,
                                                                                                            "%Y-%m-%dT%H:%M:%S.%f")))

                    # Set game start date in the past if python can't parse the date
                    # so it doesn't get flagged as live or future game and you can still play it
                    # if a video is available
                    if type(game_start_datetime_est) is not datetime.datetime:
                        game_start_datetime_est = now_datetime_est + timedelta(-30)

                    # guess end date by adding 4 hours to start date
                    game_end_datetime_est = game_start_datetime_est + timedelta(hours=4)

                    # Get playoff game number, if available
                    playoff_game_number = 0
                    playoff_status = ""
                    if self.playoff_json:
                        for game_more_data in self.playoff_json['sports_content']['games']['game']:
                            if game_more_data['game_url'] == seo_name and game_more_data.get('playoffs', ''):
                                playoff_game_number = int(game_more_data['playoffs']['game_number'])

                                if game_more_data['playoffs'].get('home_wins', None) and game_more_data['playoffs'].get('visitor_wins', None):
                                    playoff_status = "%s-%s" % (game_more_data['playoffs']['visitor_wins'], game_more_data['playoffs']['home_wins'])

                    if game_id != '':
                        # Get pretty names for the team names
                        if v.lower() in vars.config['teams']:
                            visitor_name = vars.config['teams'][v.lower()]
                        else:
                            visitor_name = v
                        if h.lower() in vars.config['teams']:
                            host_name = vars.config['teams'][h.lower()]
                        else:
                            host_name = h

                        has_video = "video" in game
                        future_video = game_start_datetime_est > now_datetime_est and \
                            game_start_datetime_est.date() == now_datetime_est.date()
                        live_video = game_start_datetime_est < now_datetime_est < game_end_datetime_est

                        # Create the title
                        name = game_start_datetime_est.strftime("%Y-%m-%d")
                        if live_video:
                            name = toLocalTimezone(game_start_datetime_est).strftime("%Y-%m-%d (at %I:%M %p)")

                        # Add the teams' names and the scores if needed
                        name += ' %s vs %s' % (visitor_name, host_name)
                        if playoff_game_number != 0:
                            name += ' (game %d)' % (playoff_game_number)
                        if vars.scores == '1' and not future_video:
                            name += ' %s:%s' % (str(vs), str(hs))

                            if playoff_status:
                                name += " (series: %s)" % playoff_status

                        thumbnail_url = ("http://i.cdn.turner.com/nba/nba/.element/img/1.0/teamsites/logos/teamlogos_500x500/%s.png" % h.lower())

                        if future_video:
                            name = "UPCOMING: " + name
                        elif live_video:
                            name = "LIVE: " + name

                        params = {
                            'name': name,
                            'video_id': game_id,
                            'seo_name': seo_name,
                            'has_away_feed': 1 if has_away_feed else 0,
                            'has_condensed_video': 1 if has_condensed_video else 0,
                            'thumbnail_url': thumbnail_url,
                            'has_video': has_video,
                            'is_future_video': future_video,
                            'is_live_video': live_video,
                            'visitor_name': v.lower(),
                            'host_name': h.lower(),
                        }

                        games.append(params)

        except Exception, e:
            utils.littleErrorPopup("Error: %s" % str(e))
            utils.log(traceback.format_exc(), xbmc.LOGDEBUG)
            pass

        return games

    def downloadPlayoffJson(self, year):
        # Download the scoreboard file for all playoffs
        scoreboard = 'http://data.nba.com/data/5s/json/cms/noseason/scoreboard/%d/playoff_all_games.json' % (year-1)
        utils.log('Requesting scoreboard: %s' % scoreboard, xbmc.LOGDEBUG)
        
        scoreboard_json = Request.getJson(scoreboard)
        if not scoreboard_json:
            return False
        if scoreboard_json and scoreboard_json.get("code", "") == "noaccess":
            return False
        return scoreboard_json

