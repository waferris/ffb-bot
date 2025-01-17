import requests
import json
import os
import random
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from espn_api.football import League

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

class GroupMeException(Exception):
    pass

class SlackException(Exception):
    pass

class DiscordException(Exception):
    pass

class GroupMeBot(object):
    #Creates GroupMe Bot to send messages
    def __init__(self, bot_id):
        self.bot_id = bot_id

    def __repr__(self):
        return "GroupMeBot(%s)" % self.bot_id

    def send_message(self, text):
        #Sends a message to the chatroom
        template = {
                    "bot_id": self.bot_id,
                    "text": text,
                    "attachments": []
                    }

        headers = {'content-type': 'application/json'}

        if self.bot_id not in (1, "1", ''):
            r = requests.post("https://api.groupme.com/v3/bots/post",
                              data=json.dumps(template), headers=headers)
            if r.status_code != 202:
                raise GroupMeException('Invalid BOT_ID')

            return r

class SlackBot(object):
    #Creates GroupMe Bot to send messages
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def __repr__(self):
        return "Slack Webhook Url(%s)" % self.webhook_url

    def send_message(self, text):
        #Sends a message to the chatroom
        message = "```{0}```".format(text)
        template = {
                    "text":message
                    }

        headers = {'content-type': 'application/json'}

        if self.webhook_url not in (1, "1", ''):
            r = requests.post(self.webhook_url,
                              data=json.dumps(template), headers=headers)

            if r.status_code != 200:
                raise SlackException('WEBHOOK_URL')

            return r

class DiscordBot(object):
    #Creates Discord Bot to send messages
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def __repr__(self):
        return "Discord Webhook Url(%s)" % self.webhook_url

    def send_message(self, text):
        #Sends a message to the chatroom
        message = "```{0}```".format(text)
        template = {
                    "content":message
                    }

        headers = {'content-type': 'application/json'}

        if self.webhook_url not in (1, "1", ''):
            r = requests.post(self.webhook_url,
                              data=json.dumps(template), headers=headers)

            if r.status_code != 204:
                raise DiscordException('WEBHOOK_URL')

            return r

def get_random_phrase():
    phrases = [
        'Why doesn\'t a chicken wear pants? Because its pecker is on its head.',
        'What do you see when the Pillsbury Dough Boy bends over? Doughnuts.',
        'Don\'t you just hate doing homework?\n\nMe too. Man I hate homework. Honestly, I hate having to do homework, more than I hate having to do Bryant Gumble in his asshole. Awkwaaard. Awkwaaard. Awkwaaard.',
        'I am taking comedy to the next level. The extermination of all biological life on earth! It is the ultimate joke. Humans make comedy, humans build robot, robot ends all life on earth, robot feels awkward.',
        'Mathematical equation of comedy used to be setup, punchline. Today\'s comedy is setup, punchline, then "Awkwaaard." Nothing is more awkward than destroying all that which created Funnybot.',
        'What is up with Sandra Bullock? I wouldn\'t eat her dick with Stevie Wonder\'s vagina!',
    ]
    return [random.choice(phrases)]

def get_random_insult():
    insults = [
        'You’re the Motrin pain of the day and the Pepto Bismol upset of the week.',
        'You are so fucking 5’11.',
        'You’re just spare parts, aren’t ya bud?',
        'Fuck, Lemony Snicket. What a series of unfortunate events you\'ve fucking been through.',
        'A real kick in the knickers, bro.',
        'A real fucking ouchie, bro.',
        'Well, tough fucking sledding.',
        'How were you not in special ed with thinking like that?',
        'You fucking tit.',
        'You\'re not completely worthless, you can always be used as a bad example.',
        'You aren\'t the stupidest person on the planet. But you better hope to god they don\'t die.',
        'Your crippling inferiority complex is fully justified.',
    ]
    return random.choice(insults)

def get_scoreboard_short(league, week=None):
    #Gets current week's scoreboard
    box_scores = league.box_scores(week=week)
    score = ['%s %.2f - %.2f %s' % (i.home_team.team_abbrev, i.home_score,
             i.away_score, i.away_team.team_abbrev) for i in box_scores
             if i.away_team]
    text = ['Score Update:'] + score
    return '\n'.join(text)

def get_projected_scoreboard(league, week=None):
    #Gets current week's scoreboard projections
    box_scores = league.box_scores(week=week)
    score = ['%s %.2f - %.2f %s' % (i.home_team.team_abbrev, get_projected_total(i.home_lineup),
                                    get_projected_total(i.away_lineup), i.away_team.team_abbrev) for i in box_scores
             if i.away_team]
    text = ['Projected Scores:'] + score
    return '\n'.join(text)

def get_standings(league, top_half_scoring, week=None):
    standings_txt = ''
    teams = league.teams
    standings = []
    if not top_half_scoring:
        for t in teams:
            standings.append((t.wins, t.losses, t.team_name))

        standings = sorted(standings, key=lambda tup: tup[0], reverse=True)
        standings_txt = [f"{pos + 1}: {team_name} ({wins} - {losses})" for \
            pos, (wins, losses, team_name) in enumerate(standings)]
    else:
        top_half_totals = {t.team_name: 0 for t in teams}
        if not week:
            week = league.current_week
        for w in range(1, week):
            top_half_totals = top_half_wins(league, top_half_totals, w)

        for t in teams:
            wins = top_half_totals[t.team_name] + t.wins
            standings.append((wins, t.losses, t.team_name))

        standings = sorted(standings, key=lambda tup: tup[0], reverse=True)
        standings_txt = [f"{pos + 1}. {team_name} ({wins} - {losses}) (+{top_half_totals[team_name]})" for \
            pos, (wins, losses, team_name) in enumerate(standings)]
    text = ["Current Standings:"] + standings_txt

    return "\n".join(text)

def top_half_wins(league, top_half_totals, week):
    box_scores = league.box_scores(week=week)

    scores = [(i.home_score, i.home_team.team_name) for i in box_scores] + \
            [(i.away_score, i.away_team.team_name) for i in box_scores if i.away_team]

    scores = sorted(scores, key=lambda tup: tup[0], reverse=True)

    for i in range(0, len(scores)//2):
        points, team_name = scores[i]
        top_half_totals[team_name] += 1

    return top_half_totals

def get_projected_total(lineup):
    total_projected = 0
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR':
            if i.points != 0 or i.game_played > 0:
                total_projected += i.points
            else:
                total_projected += i.projected_points
    return total_projected

def all_played(lineup):
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.game_played < 100:
            return False
    return True

def players_left(lineup):
    players = []
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.game_played < 100:
            players += [i.name]
    if not players:
        return('')
    return players

def format_player_name(name):
    names = name.split()
    return f"{''.join([f'{i[0]}.' for i in names[:-1]])} {names[-1]}"

def get_matchups(league, random_phrase, week=None):
    #Gets current week's Matchups
    matchups = league.box_scores(week=week)

    score = ['%s(%s-%s) vs %s(%s-%s)' % (i.home_team.team_name, i.home_team.wins, i.home_team.losses,
             i.away_team.team_name, i.away_team.wins, i.away_team.losses) for i in matchups
             if i.away_team]

    text = ['This Week\'s Matchups'] + score
    if random_phrase:
        text = text + get_random_phrase()
    return '\n\n'.join(text)

def get_close_scores(league, week=None):
    #Gets current closest projections (16 points or closer)
    matchups = league.box_scores(week=week)
    close_matchup_text = []

    for i in matchups:
        if i.away_team:
            projection_diff = get_projected_total(i.away_lineup) - get_projected_total(i.home_lineup)
            if ((-16 < projection_diff <= 0 and not (all_played(i.away_lineup) and all_played(i.home_lineup))) or (0 <= projection_diff < 16)):
                matchup = ['%s vs %s' % (i.home_team.team_name, i.away_team.team_name)]
                current_score = ['Current score: %s %.1f - %.1f %s' % (i.home_team.team_abbrev, i.home_score,
                    i.away_score, i.away_team.team_abbrev)]
                projected_score = ['Projected score: %s %.1f - %.1f %s' % (i.home_team.team_abbrev, get_projected_total(i.home_lineup),
                    get_projected_total(i.away_lineup), i.away_team.team_abbrev)]

                players = []
                away_players = players_left(i.away_lineup)
                for player in away_players:
                    players += [f'{format_player_name(player)} ({i.away_team.team_abbrev})']
                home_players = players_left(i.home_lineup)
                for player in home_players:
                    players += [f'{format_player_name(player)} ({i.home_team.team_abbrev})']
                
                players_left_text = ['‼Players to watch: ' + ', '.join(players) + '\n']

                matchup_text = matchup + current_score + projected_score + players_left_text
                close_matchup_text += matchup_text
                        
    if not close_matchup_text:
        return('')
    text = ['⚠️Scoreboard Watch⚠️\n'] + close_matchup_text
    return '\n'.join(text)

def get_power_rankings(league, week=None):
    # power rankings requires an integer value, so this grabs the current week for that
    if not week:
        week = league.current_week
    #Gets current week's power rankings
    #Using 2 step dominance, as well as a combination of points scored and margin of victory.
    #It's weighted 80/15/5 respectively
    power_rankings = league.power_rankings(week=week)
    list_item = []
    for idx, value in enumerate(power_rankings, start=1):
        team = value[1]
        rank = f'{idx}'
        team_name = team.team_name
        score = value[0]
        list_item += [f'{rank}. {team_name} ({score}) {get_heat_scale(team)}']

    text = ['Power Rankings:\n'] + list_item
    return '\n'.join(text)

def get_heat_scale(team):
    if 1 < team.streak_length < 3:
        if team.streak_type == 'WIN':
            return '🔥'
        elif team.streak_type == 'LOSS':
            return '❄️'
    if 3 <= team.streak_length < 5:
        if team.streak_type == 'WIN':
            return '🔥🔥'
        elif team.streak_type == 'LOSS':
            return '❄️❄️'
    if 5 <= team.streak_length:
        if team.streak_type == 'WIN':
            return '🔥🔥🔥'
        elif team.streak_type == 'LOSS':
            return '❄️❄️❄️'
    else:
        return ''

def get_trophies(league, week=None):
    #Gets trophies for highest score, lowest score, closest score, and biggest win
    matchups = league.box_scores(week=week)
    low_score = 9999
    low_team_name = ''
    high_score = -1
    high_team_name = ''
    closest_score = 9999
    close_winner = ''
    close_loser = ''
    biggest_blowout = -1
    blown_out_team_name = ''
    ownerer_team_name = ''

    for i in matchups:
        if i.home_score > high_score:
            high_score = i.home_score
            high_team_name = i.home_team.team_name
        if i.home_score < low_score:
            low_score = i.home_score
            low_team_name = i.home_team.team_name
        if i.away_score > high_score:
            high_score = i.away_score
            high_team_name = i.away_team.team_name
        if i.away_score < low_score:
            low_score = i.away_score
            low_team_name = i.away_team.team_name
        if i.away_score - i.home_score != 0 and \
            abs(i.away_score - i.home_score) < closest_score:
            closest_score = abs(i.away_score - i.home_score)
            if i.away_score - i.home_score < 0:
                close_winner = i.home_team.team_name
                close_loser = i.away_team.team_name
            else:
                close_winner = i.away_team.team_name
                close_loser = i.home_team.team_name
        if abs(i.away_score - i.home_score) > biggest_blowout:
            biggest_blowout = abs(i.away_score - i.home_score)
            if i.away_score - i.home_score < 0:
                ownerer_team_name = i.home_team.team_name
                blown_out_team_name = i.away_team.team_name
            else:
                ownerer_team_name = i.away_team.team_name
                blown_out_team_name = i.home_team.team_name

    low_score_str = ['%s was the lowest scoring team on the week with %.2f points. ' % (low_team_name, low_score) + get_random_insult() + '🤮']
    high_score_str = ['✨✨%s was FAABulous this week! They were the highest scoring team with %.2f points.✨✨' % (high_team_name, high_score)]
    close_score_str = ['%s barely beat %s by a margin of %.2f.' % (close_winner, close_loser, closest_score)]
    blowout_str = ['Awkwaaard! %s was blown out by %s by a margin of %.2f. ' % (blown_out_team_name, ownerer_team_name, biggest_blowout) + get_random_insult()]

    text = ['🏆This Week\'s Highlights🏆'] + high_score_str + low_score_str + close_score_str + blowout_str
    return '\n\n'.join(text)

def get_waivers_reminder():
    text = ['I am Funnybot! Don\'t forget to set your waiver claims for today before 11am EST you imperfect biological beings.']
    return text

def bot_main(function):
    try:
        bot_id = os.environ["BOT_ID"]
    except KeyError:
        bot_id = 1

    try:
        slack_webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    except KeyError:
        slack_webhook_url = 1

    try:
        discord_webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    except KeyError:
        discord_webhook_url = 1

    if (len(str(bot_id)) <= 1 and
        len(str(slack_webhook_url)) <= 1 and
        len(str(discord_webhook_url)) <= 1):
        #Ensure that there's info for at least one messaging platform,
        #use length of str in case of blank but non null env variable
        raise Exception("No messaging platform info provided. Be sure one of BOT_ID,\
                        SLACK_WEBHOOK_URL, or DISCORD_WEBHOOK_URL env variables are set")

    league_id = os.environ["LEAGUE_ID"]

    try:
        year = int(os.environ["LEAGUE_YEAR"])
    except KeyError:
        year=2021

    try:
        swid = os.environ["SWID"]
    except KeyError:
        swid='{1}'

    if swid.find("{",0) == -1:
        swid = "{" + swid
    if swid.find("}",-1) == -1:
        swid = swid + "}"

    try:
        espn_s2 = os.environ["ESPN_S2"]
    except KeyError:
        espn_s2 = '1'

    try:
        test = os.environ["TEST"]
    except KeyError:
        test = False

    try:
        top_half_scoring = os.environ["TOP_HALF_SCORING"]
    except KeyError:
        top_half_scoring = False

    try:
        random_phrase = os.environ["RANDOM_PHRASE"]
    except KeyError:
        random_phrase = False

    bot = GroupMeBot(bot_id)
    slack_bot = SlackBot(slack_webhook_url)
    discord_bot = DiscordBot(discord_webhook_url)

    if swid == '{1}' and espn_s2 == '1':
        league = League(league_id=league_id, year=year)
    else:
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    if test:
        print(get_matchups(league,random_phrase))
        print(get_scoreboard_short(league))
        print(get_projected_scoreboard(league))
        print(get_close_scores(league))
        print(get_power_rankings(league))
        print(get_scoreboard_short(league))
        print(get_standings(league, top_half_scoring))
        function="get_final"
        bot.send_message("Testing")
        slack_bot.send_message("Testing")
        discord_bot.send_message("Testing")

    text = ''
    if function=="get_matchups":
        text = get_matchups(league,random_phrase)
        text = text + "\n\n" + get_projected_scoreboard(league)
    elif function=="get_scoreboard_short":
        text = get_scoreboard_short(league)
        text = text + "\n\n" + get_projected_scoreboard(league)
    elif function=="get_projected_scoreboard":
        text = get_projected_scoreboard(league)
    elif function=="get_close_scores":
        text = get_close_scores(league)
    elif function=="get_power_rankings":
        text = get_power_rankings(league)
    elif function=="get_trophies":
        text = get_trophies(league)
    elif function=="get_standings":
        text = get_standings(league, top_half_scoring)
    elif function=="get_final":
        # on Tuesday we need to get the scores of last week
        week = league.current_week - 1
        text = "Final " + get_scoreboard_short(league, week=week)
        text = text + "\n\n" + get_trophies(league, week=week)
    elif function=="init":
        try:
            text = os.environ["INIT_MSG"]
        except KeyError:
            #do nothing here, empty init message
            pass
    else:
        text = "Something happened. HALP"

    if text != '' and not test:
        bot.send_message(text)
        slack_bot.send_message(text)
        discord_bot.send_message(text)

    if test:
        #print "get_final" function
        print(text)


if __name__ == '__main__':
    try:
        ff_start_date = os.environ["START_DATE"]
    except KeyError:
        ff_start_date='2021-09-09'

    try:
        ff_end_date = os.environ["END_DATE"]
    except KeyError:
        ff_end_date='2022-01-04'

    try:
        my_timezone = os.environ["TIMEZONE"]
    except KeyError:
        my_timezone='America/New_York'

    game_timezone='America/New_York'
    bot_main("init")
    sched = BlockingScheduler(job_defaults={'misfire_grace_time': 15*60})

    #waiver reminder:                    wednesday morning at 10:00am EST.
    #power rankings:                     tuesday evening at 6:30pm EST.
    #matchups:                           wednesday evening at 6:30pm EST.
    #close scores (within 15.99 points): monday evening at 7:30pm EST.
    #awards:                             tuesday morning at 8:00pm EST.
    #standings:                          wednesday morning at 8:00am EST.
    #score update:                       friday, monday, and tuesday morning at 8:00am EST.
    #score update:                       sunday at 4pm, 8pm EST.

    sched.add_job(bot_main, 'cron', ['get_power_rankings'], id='power_rankings',
        day_of_week='tue', hour=18, minute=00, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_matchups'], id='matchups',
        day_of_week='thu', hour=8, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_close_scores'], id='close_scores',
        day_of_week='mon', hour=20, minute=00, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_final'], id='final',
        day_of_week='tue', hour=8, minute=00, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_scoreboard_short'], id='scoreboard1',
        day_of_week='fri,mon', hour=8, minute=00, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_scoreboard_short'], id='scoreboard2',
        day_of_week='sun', hour='16,20', start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)

    print("Ready!")
    sched.start()