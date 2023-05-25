import os
import time
import discord
import requests
import matplotlib.pyplot as plt
from adjustText import adjust_text
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = discord.Client(intents=discord.Intents(messages=True, message_content=True))

# TODO before launch: add help menu, host on heroku, add help references to errors
# TODO expected guild stone leaderboard, adjust best/worst targets to expected guild stones, add num to !rg b command, fix best targets calculations, scout report modes (full, concise)
# TODO command ideas: !snitch (report who raids/guild bosses)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


@client.event
async def on_message(msg):
    message = msg.content
    author = msg.author

    if author == client.user:
        return

    # handle all commands starting with '!'
    if message.startswith('!'):
        command = message[1:].rstrip()

        # TODO add comments
        # Handle the command to send or generate the raid graph. A raid graph plots the top 50 guilds based on their
        # average rating vs average level. If no params, it will return the last saved graph.
        # Params:
        # n or new: generate a new raid graph (does not work for select)
        # a or all: label all guilds on graph
        # b or best: label top 15 guilds on graph
        # name1, name2, ... (select): label all guilds listed
        # dice: label all dice guilds
        if command.startswith('rg') or command.startswith('raidgraph'):
            # handle select mode
            if ',' in command:
                # TODO check if this is right
                params = [command.split()[0], command[command.index(' ')+1:].split(', ')[0:]]
            else:
                params = command.lower().split()

            try:
                if params[1] == 'a' or params[1] == 'all':
                    await msg.channel.send(file=discord.File('./raidgraph_all.png'))
                    return
                elif params[1] == 'b' or params[1] == 'best':
                    await msg.channel.send(file=discord.File('./raidgraph_best.png'))
                    return
                elif params[1] == 'dice':
                    await msg.channel.send(file=discord.File('./raidgraph_dice.png'))
                    return
                elif params[1] == 'n' or params[1] == 'new' or type(params[1]) is list:
                    try:
                        if params[2] == 'a' or params[2] == 'all':
                            mode = 'all'
                            mode_string = ' in All Mode'
                        elif params[2] == 'b' or params[2] == 'best':
                            mode = 'best'
                            mode_string = ' in Best Mode'
                        elif params[2] == 'dice':
                            mode = 'dice'
                            mode_string = ' in DICE Mode'
                        else:
                            await msg.channel.send(f"> `Unknown parameter: {params[2]}. Try using !help`")
                            return
                    except IndexError:
                        if type(params[1]) is list:
                            mode = params[1]
                            mode_string = ' in Select Mode'
                        else:
                            mode = 'all'
                            mode_string = ' in All Mode'

                    await msg.channel.send(f"> `Generating New Raid Graph{mode_string}. This might take a few seconds...`")
                    try:
                        top_guilds = get_top_guilds()
                    except Exception as e:
                        await msg.channel.send(e)
                        return
                    try:
                        top_guilds_info = get_top_guilds_info(top_guilds)
                    except Exception as e:
                        await msg.channel.send(e)
                        return

                    generate_raid_graph(top_guilds_info, mode)
                    if type(params[1]) is list:
                        await msg.channel.send(file=discord.File('./raidgraph_select.png'))
                        return
                    else:
                        await msg.channel.send(file=discord.File(f"./raidgraph_{mode}.png"))
                        return
                else:
                    await msg.channel.send(f"> `Unknown parameter: {params[1]}. Try using !help`")
                    return
            except IndexError:
                await msg.channel.send(file=discord.File('./raidgraph_all.png'))
                return

        # Handle the command to generate a scout report. The scout report includes average guild rating and level, best
        # member targets, most common squads, most common heroes, and projected guild stones (in progress).
        if command.startswith('s') or command.startswith('scout'):
            await msg.channel.send('> `Generating Scout Report. This might take a few seconds...`')
            guild = command[command.index(' ')+1:].lower()
            try:
                scout_report = scout(guild)
                if len(scout_report) > 2000:
                    scout_report_parts = scout_report.split('```', 5)
                    scout_report = ['```'.join(scout_report_parts[:5]), '```' + '```'.join(scout_report_parts[5:])]
                    await msg.channel.send(f"{scout_report[0]}")
                    await msg.channel.send(f"{scout_report[1]}")
                else:
                    await msg.channel.send(f"{scout_report}")
                await msg.channel.send(file=discord.File('./guildgraph.png'))

            except Exception as e:
                await msg.channel.send(e)
                return

        if command.startswith('h') or command.startswith('help'):
            help_message = ''
            help_message += '### DICE Scout Usage Guide\n'
            help_message += '> **!raidgraph or !rg:**\n'
            help_message += '```Generates a graph of the top 50 guilds. Guilds are positioned based on the total average rating and level of all guild members. Points on the graph can be 3 different types, a red X (bad level:rating ratio), a yellow circle (okay level:rating ratio), or a green star (good level:rating ratio). This does not necessarily mean they are the best guilds to raid but use your judgement for your own strength.```\n'
            help_message += '**Parameters:**\n'
            help_message += '* ***n or new:** generates a new graph (if n is not used, the most recent generated graph will be sent)*\n'
            help_message += '* ***a or all:** all guilds will be labeled (default if no other mode is set)*\n'
            help_message += '* ***b or best:** only 15 best level:rating ratio guilds will be labeled*\n'
            help_message += '* ***guild1, guild2, ... :** only guilds specified will be labeled (do not use n parameter, it will generate new by default)*\n'
            help_message += '* ***dice:** only DICE family guilds will be labeled*\n\n'
            help_message += '**Example Usages:**\n'
            help_message += '* ***!rg n*** - will generate a new graph with all guilds labeled\n'
            help_message += '* ***!rg a*** - will send the most recently generated graph with all guilds labeled\n'
            help_message += '* ***!raidgraph new best*** - will generate a new graph with 15 best level:rating ratio guilds labeled\n\n'
            help_message += '> **!scout or !s:**\n'
            help_message += '```Generates a scout report for specified guild. The scout report includes: average guild rating/level and rating/level spread, expected total guild stones (in progress), best targets, most common active squads/heroes, and a guild graph. The guild graph follows the same rules as raid graph in terms of position and point meanings.```\n'
            help_message += '**Parameters:**\n'
            help_message += '* ***<Guild Name>:*** Generates a new scout report\n\n'
            help_message += '**Example Usages:**\n'
            help_message += '* ***!s Dark n DICE*** - will generate a new scout report for the guild \'Dark n DICE\'\n\n'
            help_message += '> **!help or !h:**\n'
            help_message += '```Displays the help/usage guide.```\n'
            help_message += '> **General info**\n'
            help_message += '* Commands and guilds are not case-sensitive. \'Dark n DICE\' and \'dark n dice\' are treated the same.\n'
            help_message += '* Feel free to send any suggestions or bug reports to me on disc: Trippy#1712 or ping me @xTrippy'

            await msg.channel.send(help_message)


# TODO add comments
def scout(guild):
    scout_report = ''
    try:
        guild, members = get_guild_member_info(guild)
    except Exception as e:
        raise Exception(e)

    avg_level = round(sum(member['Level'] for member in members) / len(members))
    level_spread = f"{min(member['Level'] for member in members)} - {max(member['Level'] for member in members)}"
    avg_rating = round(sum(member['Rating'] for member in members) / len(members))
    rating_spread = f"{min(member['Rating'] for member in members)} - {max(member['Rating'] for member in members)}"

    best_targets = sorted(members, key=lambda x: x['Level'] / x['Rating'], reverse=True)[:5]
    best_targets_string = '\n'.join([
        f"{member['Name']: <16} (Lvl {member['Level']: <3}, Rating: {member['Rating']: <5}): [{', '.join(member['HeroNames'])}]"
        for member in best_targets])

    squad_count = Counter(tuple(sorted(member['HeroNames'])) for member in members)
    squad_count_string = '\n'.join([
        f"{', '.join(squad)} - {count} times ({', '.join(member['Name'] for member in members if tuple(sorted(member['HeroNames'])) == squad)})"
        for squad, count in sorted(squad_count.items(), key=lambda x: x[1], reverse=True)])

    hero_count = Counter(hero for member in members for hero in member['HeroNames'])
    hero_count_string = "\n".join([
        f"{hero: <14} {count: <2} - {count / len(members) * 100:.2f}%"
        for hero, count in sorted(hero_count.items(), key=lambda x: x[1], reverse=True)])

    generate_guild_graph(guild, members)

    note = '*Note: this data is only currently active squad, not necessarily raid/arena squad (updated every ~4hrs)*'
    scout_report += f"> ## :crossed_swords:   {guild}   :crossed_swords:\n"
    scout_report += f"> ### :trident:   Average Level:  {avg_level}  ({level_spread})   :trident:\n"
    scout_report += f"> ### :trophy:   Average Rating:  {avg_rating}  ({rating_spread})   :trophy:\n"
    scout_report += f"> ### :herb:   Expected Guild Stones:  in progress   :herb:\n"
    scout_report += f"> ### :dart:   Best Targets:\n```{best_targets_string}```\n"
    scout_report += f'> ### :man_superhero:   Active Hero Squads:\n{note}```{squad_count_string}```'
    scout_report += f'```{hero_count_string}```'

    return scout_report


# Used in scout() for get all member info for scout report
def get_guild_member_info(guild):
    # GET request for all guild members info in guild
    url = 'https://api.autobattles.online/api/v1/Guild'
    params = {'name': guild}
    response = requests.get(url, params=params)

    if 'title' in response.json() and response.json()['title'] == 'Not Found':
        raise Exception('> `Error: Guild not found`')

    if response.status_code != 200:
        raise Exception('> `Error: Failed to get guild\'s members for scout report`')

    # Collect list of dictionaries for each member of guild in format:
    # {'Name': 'DaddyJoe',
    # 'Rating': 8305,
    # 'Level': 624,
    # 'SeasonWins': 10891,
    # 'HeroNames': ['Cupid', 'Bloody Mary', 'Lucky', 'Arachne', 'Gingie']},
    # {'Name': 'ChillPower',
    # 'Rating': 4969,
    # 'Level': 630,
    # 'SeasonWins': 18049,
    # 'HeroNames': ['Santa', 'Arachne', 'Brynhildr', 'Tesla', 'Gingie']}
    # ...
    guild = response.json()['Guild']
    fields = ['Name', 'Rating', 'Level', 'SeasonWins']
    name = guild['Name']
    members = [{key: value for key, value in member.items() if key in fields} for member in guild['Members']]
    # Append squads to each member's info. Raises 'Failed to get squad' error on failed GET request
    try:
        members = get_guild_member_squads(members)
    except Exception as e:
        raise Exception(e)

    # Returns guild name and member info list
    return name, members


# Helper method for get_guild_member_info() to add each member's squad to their info dictionary
def get_guild_member_squads(members):
    # GET request for all members in guild's squad
    url = 'https://api.autobattles.online/api/v2/Squad/Arena/Users'
    names = ', '.join([member['Name'] for member in members])
    params = {'names': names}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception('> `Error: Failed to get guild\'s members\'s squads for scout report`')

    # Adds all hero squads to each member's info dictionary
    squads = {member['Name']: member['HeroNames'] for member in response.json()['Users']}
    for member in members:
        member['HeroNames'] = squads.get(member['Name'], [])

    return members


# Used in !rg command processing to return list of guilds. Provides the list for get_top_guilds_info() GET request
def get_top_guilds():
    # GET request for current top 50 guilds. There are 2 requests due to Web API limit of 30 guilds per request
    url = 'https://api.autobattles.online/api/v1/Leaderboard/Guilds/Range'
    params = {
        'position': 0,
        'count': 30,
    }
    params2 = {
        'position': 30,
        'count': 20,
    }
    response1 = requests.get(url, params=params)
    response2 = requests.get(url, params=params2)

    if response1.status_code != 200 or response2.status_code != 200:
        raise Exception('> `Error: Failed to get top guilds`')

    # Merge requests together and strip only guild names
    guilds = response1.json()['Guilds'] + response2.json()['Guilds']
    guild_names = [guild['Name'] for guild in guilds]

    return guild_names


# Used in !rg command processing to return dictionary of guilds with the value of each guild being the member list.
# Provides the dictionary for generate_raid_graph() to compute the results
def get_top_guilds_info(guilds):
    # GET request for each guild's information (rating and level). There are 2 requests due to Web API limit of 30
    # guilds per request
    url = 'https://api.autobattles.online/api/v1/Guild/Members/Bulk'
    guild_string1 = ", ".join(guilds[:26])
    guild_string2 = ", ".join(guilds[26:])
    params1 = {'names': guild_string1}
    params2 = {'names': guild_string2}
    response1 = requests.get(url, params=params1)
    response2 = requests.get(url, params=params2)

    if response1.status_code != 200 or response2.status_code != 200:
        raise Exception('> `Error: Failed to get guilds\' members for raid graph`')

    # Generate dictionary of guilds, each keyed to a list of dictionaries for each member of the guild
    guild_info = response1.json()['Guilds'] + response2.json()['Guilds']
    info = {}
    fields = ['Rating', 'Level']
    for guild in guild_info:
        members = [{key: value for key, value in member.items() if key in fields} for member in guild['Members']]
        info[guild['Name']] = members

    return info


# TODO update comments
# Generates and labels a scatter plot for each of the top 50 guilds' average rating and level. Then saves the plot as
# raidgraph.png. Gets created when !rg new is used.
def generate_raid_graph(guilds, mode):
    curr_time = time.strftime("%m-%d-%y %H:%M EST", time.localtime(time.time()))

    averages = {guild: {'Rating': sum(member['Rating'] for member in members) / len(members),
                        'Level': sum(member['Level'] for member in members) / len(members)}
                for guild, members in guilds.items()}
    ratings = [guild['Rating'] for guild in averages.values()]
    levels = [guild['Level'] for guild in averages.values()]

    sorted_guilds = sorted(averages.items(), key=lambda x: x[1]['Level'] / x[1]['Rating'], reverse=True)
    best_targets = sorted_guilds[:15]
    mid_targets = sorted_guilds[15:35]
    worst_targets = sorted_guilds[35:]

    plt.cla()

    for guild in best_targets:
        plt.plot(guild[1]['Rating'], guild[1]['Level'], 'g*', markersize=8)
    for guild in mid_targets:
        plt.plot(guild[1]['Rating'], guild[1]['Level'], 'yo', markersize=5)
    for guild in worst_targets:
        plt.plot(guild[1]['Rating'], guild[1]['Level'], 'rX', markersize=6)

    # Buffer for plot zoom
    x_buffer = (max(ratings) - min(ratings)) * 0.1
    y_buffer = (max(levels) - min(levels)) * 0.1
    # Set limits for the x-axis and y-axis with buffer values
    plt.xlim(min(ratings) - x_buffer, max(ratings) + x_buffer)
    plt.ylim(min(levels) - y_buffer, max(levels) + y_buffer)

    if mode == 'all':
        texts = [plt.text(r, l, guild, fontsize=6) for r, l, guild in zip(ratings, levels, averages.keys())]
        adjust_text(texts, force_text=0.2, force_points=20, precision=0.001, autoalign='xy',
                    only_move={'points': 'x', 'text': 'y'}, arrowprops=dict(arrowstyle='-', color='red'))
    elif mode == 'best':
        texts = [plt.text(guild[1]['Rating'], guild[1]['Level'], guild[0], fontsize=6) for guild in best_targets]
        adjust_text(texts, force_text=0.2, force_points=20, precision=0.001, autoalign='xy',
                    only_move={'points': 'x', 'text': 'y'}, arrowprops=dict(arrowstyle='-', color='red'))
    elif type(mode) is list:
        guild_keys = {guild_name.lower(): guild_name for guild_name in averages}
        texts = []
        not_found = []
        for guild in mode:
            if guild.lower() in guild_keys:
                texts.append(plt.text(averages[guild_keys[guild.lower()]]['Rating'], averages[guild_keys[guild.lower()]]['Level'], guild_keys[guild.lower()], fontsize=6))
            else:
                not_found.append(guild)

        adjust_text(texts, force_text=0.2, force_points=20, precision=0.001, autoalign='xy',
                    only_move={'points': 'x', 'text': 'y'}, arrowprops=dict(arrowstyle='-', color='red'))
    elif mode == 'dice':
        dice = ['Dark n DICE', 'Frost n DICE', 'Krakens of Dice', 'DICE', 'Dice Balance', 'SPQR DICE', 'ParaDICE',
                'Less Equites', 'LESS Br']
        texts = []

        for guild in dice:
            try:
                texts.append(plt.text(averages[guild]['Rating'], averages[guild]['Level'], guild, fontsize=6))
            except KeyError:
                continue

        adjust_text(texts, force_text=0.2, force_points=20, precision=0.001, autoalign='xy',
                    only_move={'points': 'x', 'text': 'y'}, arrowprops=dict(arrowstyle='-', color='red'))

    if type(mode) is list:
        mode = 'select'
    plt.xlabel('Average Member Rating')
    plt.ylabel('Average Member Level')
    plt.title(f"Raid Graph ({mode.capitalize()}) - {curr_time}")
    plt.savefig(f"./raidgraph_{mode}.png")


# TODO add comments
def generate_guild_graph(guild, members):
    curr_time = time.strftime("%m-%d-%y %H:%M EST", time.localtime(time.time()))

    ratings = [member['Rating'] for member in members]
    levels = [member['Level'] for member in members]
    names = [member['Name'] for member in members]

    sorted_members = sorted(members, key=lambda x: x['Level'] / x['Rating'], reverse=True)
    best_targets = sorted_members[:5]
    mid_targets = sorted_members[5:10]
    worst_targets = sorted_members[10:]

    plt.cla()

    for member in best_targets:
        plt.plot(member['Rating'], member['Level'], 'g*', markersize=8)
    for member in mid_targets:
        plt.plot(member['Rating'], member['Level'], 'yo', markersize=5)
    for member in worst_targets:
        plt.plot(member['Rating'], member['Level'], 'rX', markersize=6)

    # Buffer for plot zoom
    x_buffer = (max(ratings) - min(ratings)) * 0.1
    y_buffer = (max(levels) - min(levels)) * 0.1
    # Set limits for the x-axis and y-axis with buffer values
    plt.xlim(min(ratings) - x_buffer, max(ratings) + x_buffer)
    plt.ylim(min(levels) - y_buffer, max(levels) + y_buffer)

    texts = [plt.text(r, l, name, fontsize=8) for r, l, name in zip(ratings, levels, names)]
    adjust_text(texts, precision=0.001, autoalign='xy', expand_text=(1.0, 1.5), expand_points=(1.5, 3.0), force_points=1.05,
                only_move={'points': 'x', 'text': 'y'}, arrowprops=dict(arrowstyle='-', color='black'))

    plt.xlabel('Member Rating')
    plt.ylabel('Member Level')
    plt.title(f"{guild} Member Graph - {curr_time}")
    plt.savefig('./guildgraph.png')


client.run(TOKEN)
