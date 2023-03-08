from csv import excel
from hashlib import new
import discord
import time
import random
import json
import sys

from discord import channel

client = discord.Client()

with open('botKey.txt') as f:
    botKey = f.readline()

gameOn = False

## Bot methods
def setupStatTracking(players, startLimit, caller):
    '''
    Creates and returns a dictionary that will store user information for the current deathroll game.

            Parameters:
                    players (list): A list that contains all Discord Users involved in this deathroll game
                    startLimit (int): The value the deathroll game started at

            Returns:
                    data (dict): A dictionary set up to store the game's starting value as well as
                                 keys for each player involved in the game (this will represent the
                                 player's highest cut during this game. Initially 0)
    '''
    data = {"highest_start": startLimit}
    data["roll_starter"] = caller.name
    # This is just going to store each player's biggest cuts this game
    for player in players:
        data[player.name] = {}
        data[player.name]["biggest_cut"] = 0
        data[player.name]["cuts"] = 0
        data[player.name]["crit_cuts"] = 0
        data[player.name]["stalls"] = 0

    return data

def AshLikelyLoses(limit, playerName):
    if playerName.name == "Ash":
        return min(roll(limit), roll(limit), roll(limit))
    else:
        return roll(limit)

def updateTracker(tracker, curPlayer, oldLim, newLim, nRounds, isCut, isCrit, fin = False):
    cut = oldLim - newLim
    if cut > tracker[curPlayer.name]["biggest_cut"]:
        tracker[curPlayer.name]["biggest_cut"] = cut
    if isCut:
        tracker[curPlayer.name]["cuts"] += 1
    if isCrit:
        tracker[curPlayer.name]["crit_cuts"] += 1
    if cut == 0:
        tracker[curPlayer.name]["stalls"] += 1
    # Game is over. Record who lost and how many rounds we went
    if fin:
        tracker["nRounds"] = nRounds
        tracker["loser"] = curPlayer.name
        tracker["cutToL"] = cut
    return cut


def updateTrackerFile(tracker, players):
    # TODO: Remove the bloat, dawg

    # Want to try and open a file if it's already there
    try:
        with open('stat_tracker.json') as f:
            data = json.load(f)
            # Update General Info
            if len(players) > data["general"]["most_players"]:
                data["general"]["most_players"] = len(players)
            if tracker["nRounds"] > data["general"]["longest_game"]:
                data["general"]["longest_game"] = tracker["nRounds"]
            # Update Player Info
            for player in players:
                # Make sure player is in data. Add them if needed
                # TODO: Add new stats
                if player.name not in data["player_stats"].keys():
                    data["player_stats"][player.name] = {"wins": 0, "losses": 0, "self_destructs": 0, "biggest_cut": 0, "cutToL" : 0,
                     "most_cuts" : 0, "most_crit_cuts" : 0, "cuts" : 0, "crit_cuts" : 0, "stalls" : 0, "spooky_shillings": 0, "accolades": []}

                # --- CUT INFO --- #
                if tracker[player.name]["biggest_cut"] > data["general"]["biggest_cut"]:
                    data["general"]["biggest_cut"] = tracker[player.name]["biggest_cut"]
                    data["general"]["biggest_cut_maker"] = player.name
                if tracker[player.name]["cuts"] > data["player_stats"][player.name]["most_cuts"]:
                    data["player_stats"][player.name]["most_cuts"] = tracker[player.name]["cuts"]
                if tracker[player.name]["crit_cuts"] > data["player_stats"][player.name]["most_crit_cuts"]:
                    data["player_stats"][player.name]["most_crit_cuts"] = tracker[player.name]["crit_cuts"]
                data["player_stats"][player.name]["cuts"] += tracker[player.name]["cuts"]
                data["player_stats"][player.name]["crit_cuts"] += tracker[player.name]["crit_cuts"]
                data["player_stats"][player.name]["stalls"] += tracker[player.name]["stalls"]

                # --- BASIC INFO --- #
                if tracker[player.name]["biggest_cut"] > data["player_stats"][player.name]["biggest_cut"]:
                    data["player_stats"][player.name]["biggest_cut"] = tracker[player.name]["biggest_cut"]
                if player.name == tracker["loser"]:
                    data["player_stats"][player.name]["losses"] += 1
                    if data["player_stats"][player.name]["cutToL"] < tracker["cutToL"]:
                        data["player_stats"][player.name]["cutToL"] = tracker["cutToL"]
                    # If we started the game and lost...
                    if player.name == tracker["roll_starter"]:
                        # Increase player's self destruct value
                        data["player_stats"][player.name]["self_destructs"] += 1
                        # Every 5 losses, gain a force add point
                        if data["player_stats"][player.name]["losses"] % 5 == 0:
                            data["player_stats"][player.name]["spooky_shillings"] += 1
                else:
                    data["player_stats"][player.name]["wins"] += 1
                    # If we won and didn't initiate the deathroll, gain a force add point, up to a max of 5
                    if player.name != tracker["roll_starter"] and data["player_stats"][player.name]["spooky_shillings"] < 5:
                        data["player_stats"][player.name]["spooky_shillings"] += 1

            # Now we need to go through every entry in our player stats to update some general stuff
            highest_wl = 0
            lowest_wl = 9999
            most_cuts = 0
            most_crits = 0
            biggest_cut_to_L = 0
            avg_crits_per_game = 0
            avg_cuts_pers_game = 0
            most_stalls = 0
            most_games = 0
            most_sds = 0
            # TODO: Is there a better way to do this?
            for entry in data["player_stats"]:
                try:
                    ratio = data["player_stats"][entry]["wins"] / (data["player_stats"][entry]["wins"] + data["player_stats"][entry]["losses"])
                except:
                    continue
                # Check for best win / loss
                if ratio > highest_wl:
                    highest_wl = ratio

                # Check for worst win / loss
                if ratio < lowest_wl:
                    lowest_wl = ratio

                if data["player_stats"][entry]["wins"] + data["player_stats"][entry]["losses"] > most_games:
                    most_games = data["player_stats"][entry]["wins"] + data["player_stats"][entry]["losses"]

                if data["player_stats"][entry]["stalls"] > most_stalls:
                    most_stalls = data["player_stats"][entry]["stalls"]

                if data["player_stats"][entry]["cuts"] > most_cuts:
                    most_cuts = data["player_stats"][entry]["cuts"]

                if data["player_stats"][entry]["crit_cuts"] > most_crits:
                    most_crits = data["player_stats"][entry]["crit_cuts"]

                if data["player_stats"][entry]["cutToL"] > biggest_cut_to_L:
                    biggest_cut_to_L = data["player_stats"][entry]["cutToL"]

                if data["player_stats"][entry]["self_destructs"] > most_sds:
                    most_sds = data["player_stats"][entry]["self_destructs"]

                cuts_per_game = data["player_stats"][entry]["cuts"] / (data["player_stats"][entry]["wins"] + data["player_stats"][entry]["losses"])
                crits_per_game = data["player_stats"][entry]["crit_cuts"] / (data["player_stats"][entry]["wins"] + data["player_stats"][entry]["losses"])

                if avg_cuts_pers_game < cuts_per_game:
                    avg_cuts_pers_game  = cuts_per_game
                if avg_crits_per_game < crits_per_game:
                    avg_crits_per_game = crits_per_game

            # Update General Info
            data["general"]["worst_wl_ratio"] = lowest_wl
            data["general"]["best_wl_ratio"] = highest_wl
            data["general"]["top_crits"] = most_crits
            data["general"]["top_cutter"] = most_cuts

            # Now we can assign titles
            # TODO: The general way to update these are the same, see if you can wrap it up into a loop instead of a manual thing...
            for entry in data["player_stats"]:
                wins = data["player_stats"][entry]["wins"]
                losses = data["player_stats"][entry]["losses"]
                try:
                    ratio = wins / (wins + losses)
                except:
                    continue

                avg_cuts = data["player_stats"][entry]["cuts"] / (data["player_stats"][entry]["wins"] + data["player_stats"][entry]["losses"])
                avg_crits = data["player_stats"][entry]["crit_cuts"] / (data["player_stats"][entry]["wins"] + data["player_stats"][entry]["losses"])
                
                # --- TOP CUTTER --- #
                if data["player_stats"][entry]["cuts"] >= data["general"]["top_cutter"]:
                    data["general"]["top_cutter"] = data["player_stats"][entry]["cuts"]
                    if "Top Cutter" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Top Cutter")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Top Cutter")
                    except:
                        pass
               
                # --- CRITICALLY MINDED --- #
                if data["player_stats"][entry]["crit_cuts"] >= data["general"]["top_crits"]:
                    data["general"]["top_crits"] = data["player_stats"][entry]["crit_cuts"]
                    if "Critically Minded" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Critically Minded")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Critically Minded")
                    except:
                        pass
                
                # --- LOSS AVERTER --- #
                if ratio >= data["general"]["best_wl_ratio"]:
                    data["general"]["best_wl_ratio"] = ratio
                    if "Loss Averter" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Loss Averter")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Loss Averter")
                    except:
                        pass
                
                # --- CAPTAIN COPE --- #
                if ratio <= data["general"]["worst_wl_ratio"]:
                    data["general"]["worst_wl_ratio"] = ratio
                    if "Captain Cope" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Captain Cope")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Captain Cope")
                    except:
                        pass
                
                # --- SPEED RUNNER --- #
                if data["player_stats"][entry]["cutToL"] >= biggest_cut_to_L:
                    if "Speed Runner" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Speed Runner")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Speed Runner")
                    except:
                        pass
                
                # --- SPRINTER --- #
                if avg_cuts >= avg_cuts_pers_game:
                    if "Sprinter" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Sprinter")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Sprinter")
                    except:
                        pass
                
                # --- ADRENALINE JUNKIE --- #
                if avg_crits >= avg_crits_per_game:
                    if "Adrenaline Junkie" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Adrenaline Junkie")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Adrenaline Junkie")
                    except:
                        pass

                # --- COMMITTED --- #
                if wins+losses >= most_games:
                    if "Committed" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Committed")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Committed")
                    except:
                        pass

                # --- IMMOVABLE OBJECT --- #
                if data["player_stats"][entry]["stalls"] >= most_stalls:
                    if "Immovable Object" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Immovable Object")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Immovable Object")
                    except:
                        pass

                # --- Suicide Bomber --- #
                if data["player_stats"][entry]["self_destructs"] >= most_sds:
                    if "Suicide Bomber" not in data["player_stats"][entry]["accolades"]:
                        data["player_stats"][entry]["accolades"].append("Suicide Bomber")
                else:
                    # Try to remove it if it no longer applies
                    try:
                        data["player_stats"][entry]["accolades"].remove("Suicide Bomber")
                    except:
                        pass

                # Finally, sort accolades to be alphabetical
                # data["player_stats"][entry]["accolades"].sort() # NOT SURE IF I WANT TO DO THIS


        
        # Now write to file
        with open('stat_tracker.json', 'w') as f:
            json_string = json.dumps(data)
            f.write(json_string)

    # If no stat tracking file exists, make one
    # TODO: Make the file lol
    except Exception as e:
            print(e)

def pullStats(message, player = None):
    '''
    Given a message that calls for stats, create a formatted embed that the bot can send in a message

            Parameters:
                    message (Message): The Discord Message that called for a game to start
                    player (str or List): A string or list of strings for a player's name. List happens when a name has spaces

            Returns:
                    embedVar: A formatted embed that contains certain player stats
    '''
    # Make note of who sent the message. We might want to pull stats for this person
    caller = message.author

    # If we're not given a specific name to get stats for, assume the caller wants their own stats
    if player is None:
        player = caller.name
    elif isinstance(player, list):
        # This is how we're gonna deal with instances where a person's name is coming as a list due to spaces
        # TODO: Better way to do this?
        player = " ".join(player)

    # Want to try and open a file if it's already there
    try:
        with open('stat_tracker.json') as f:
            data = json.load(f)

        wins = data["player_stats"][player]["wins"]
        losses = data["player_stats"][player]["losses"]
        ratio = round((wins / (wins + losses)) * 100, 2)

        # This is just a quick way to change the embed's side banner color
        #   Side banner will be blue if win / loss ratio is above 50%, and red otherwise
        if ratio >= 50:
            embedVar = discord.Embed(color=0x0B5394, title = player)
        else:
            embedVar = discord.Embed(color=0xE74C3C , title = player)
        #embedVar.set_author(name = caller.name)
        #embedVar.set_thumbnail(url= caller.default_avatar)
        #embedVar.add_field(name= "\u200B", value = "\u200B", inline=False)
        #embedVar.add_field(name= "\u200B", value = "\u200B", inline=False)
        embedVar.add_field(name= "Wins: ", value = wins, inline=True)
        embedVar.add_field(name= "Losses: ", value = losses, inline=True)
        embedVar.add_field(name= "Win / Loss Ratio: ", value = str(ratio) + "%", inline=True)
        embedVar.add_field(name= "Biggest Cut to Loss: ", value = data["player_stats"][player]["cutToL"], inline=False)
        embedVar.add_field(name= "Most Cuts in a Game: ", value = data["player_stats"][player]["most_cuts"], inline=True)
        embedVar.add_field(name= "Total Cuts: ", value = data["player_stats"][player]["cuts"], inline=True)
        embedVar.add_field(name= "Most Critical Cuts in a Game: ", value = data["player_stats"][player]["most_crit_cuts"], inline=False)
        embedVar.add_field(name= "Total Critical Cuts: ", value = data["player_stats"][player]["crit_cuts"], inline=True)
        embedVar.add_field(name= "Total Stalls: ", value = data["player_stats"][player]["stalls"], inline=True)
        embedVar.set_footer(text = "Current Titles: " +  ', '.join(str(n) for n in data["player_stats"][player]["accolades"]))

        return embedVar

    # If no stat tracking file exists, make one
    # TODO: Make the file...
    except:
        print("Error pulling stats!")

def displayTitles():
    # TODO: Maybe consider storing these in a dictionary somewhere so we can easily iterate through them
    #       instead of manually going 1 by 1
    embedVar = discord.Embed(color=0xd4ac0d, title = "Deathroll Titles")
    embedVar.add_field(name= "Adrenaline Junkie: ", value = "Have the highest average critical cuts per game", inline=False)
    embedVar.add_field(name= "Captain Cope: ", value = "Have the lowest win / loss ratio", inline=False)
    embedVar.add_field(name= "Committed: ", value = "Have the most games played", inline=False)
    embedVar.add_field(name= "Critically Minded: ", value = "Have the highest amount of critical cuts", inline=False)
    embedVar.add_field(name= "Immovable Object: ", value = "Have the most stalls", inline=False)
    #embedVar.add_field(name= "Lonely: ", value = "Start the most deathroll games and have no one join", inline=False)
    embedVar.add_field(name= "Loss Averter: ", value = "Have the highest win / loss ratio", inline=False)
    #embedVar.add_field(name= "Party Starter: ", value = "Start the most deathroll games", inline=False)
    #embedVar.add_field(name= "Peskiest: ", value = "Start the most deathroll games", inline=False)
    #embedVar.add_field(name= "Popular: ", value = "Get the most people to join a deathroll", inline=False)
    embedVar.add_field(name= "Speed Runner: ", value = "Have the highest cut to loss", inline=False)
    embedVar.add_field(name= "Sprinter: ", value = "Have the highest average cuts per game", inline=False)
    embedVar.add_field(name= "Suicide Bomber: ", value = "Start and lose a bunch of games", inline=False)
    #embedVar.add_field(name= "Survivor: ", value = "Avoid losing many games in a row", inline=False)
    embedVar.add_field(name= "Top Cutter: ", value = "Have the highest amount of cuts", inline=False)

    return embedVar

def roll(num):
    return random.randint(1, int(num))

def getLeaderboard():
    '''
    Read our stat tracking file to create a leaderboard embed that the bot can later send

            Parameters:

            Returns:
                    embedVar: The formatted leaderboard embed that will display in a message sent by the bot
    '''
    try:
        with open('stat_tracker.json') as f:
            data = json.load(f)
    except Exception as e:
        print(e)

    info = []
    
    # Gather player information from the json file
    for entry in data["player_stats"]:
        wins = data["player_stats"][entry]["wins"]
        losses = data["player_stats"][entry]["losses"]
        try:
            ratio = round((wins / (wins + losses)) * 100, 2)
        except:
            continue
        info.append((entry, ratio, data["player_stats"][entry]["accolades"]))

    # Sort our gathered information by the win/loss ratio
    info = sorted(info, key=lambda tup: tup[1], reverse=True)

    embedVar = discord.Embed(color=0xd4ac0d, title = "Deathroll Leaderboard")
    for entry in info:
        #embedVar.add_field(name= str(entry[0]), value = str(entry[1]) + '% Titles: '.join(str(n) for n in entry[2]), inline=False)
        embedVar.add_field(name= str(entry[0]), value = str(entry[1]) + '%', inline=False)

        #"Current Titles: " +  '   '.join(str(n) for n in data["player_stats"][caller.name]["accolades"]

    return embedVar

# TODO: Figure this out...
def getWager(message):
    pass

def getParams(message):
    '''
    Given the message that call for a deathroll run (ex: !deathroll 42), return the desired starting value

            Parameters:
                    message (Message): The Discord Message that called for a game to start

            Returns:
                    num (int): The number in which a user wanted a deathroll game to start at
                    isRandom (boolean): A flag that will indicate whether or not our number parameter was randomly generated
                    startDelay (int): The duration in seconds to wait before we tally players
    '''
    # Formatting to allow for the following format: !deathroll 42
    # Above would return 42, False
    # Formatting to allow for the following format with specified delay: !deathroll 42 25
    # Above would return 42, False, 25
    # Formatting to allow for the following format with specified delay: !deathroll random 18
    # Above would return a randomly generated number, True, 18
    content = (message.content).split()

    # Check to see if a delay before start was specified
    startDelay = 10
    if len(content) > 2 and "@" not in content[2]:     # TODO: Figure out a better way for this. This second half is just to ensure we don't confuse this for mentions
        startDelay = int(content[2])
        if startDelay > 30:
            startDelay = 30


    # Check if string "random" was sent. If so, we'll just randomly generate and return a
    # starting value between 1 and 1,000,000
    if "random" in message.content.lower():
        return random.randint(1, 1000000), True, startDelay, False

    # Do a quick check on the value sent. If <= 1, use 2
    try:
        val = max(2, abs(int(float(content[1]))))
    except:
        return random.randint(1, 1000000), True, startDelay, True

    # Return value
    return val, False, startDelay, False

async def gatherPlayers(message, caller, callOuts = []):
    '''
    Pull reactions from the Bot's pre-game message. Whoever initialized the deathroll game will be
    the first in the player list

            Parameters:
                    message (Message): The message the Bot sent prior to the game starting
                    caller (User): The Discord User that had done the !deathroll call
                    callOuts (List of Users): List of users mentioned in the caller's !deathroll command call

            Returns:
                    players (list): A list of each Discord User that had reacted to the given message
    '''
    message = await message.channel.fetch_message(message.id)
    players = [caller] + callOuts
    reacts = message.reactions
    for react in reacts:
        async for user in react.users():
            # Don't want to include people twice. Also don't want the bot to be a player
            if user not in players and user.id != message.author.id:
                players.append(user)
            print('{0} has reacted with {1.emoji}!'.format(user, react))
    return players

def updatePlayerCallOuts(player, change):
    '''
    Update the given player's allow call outs. Stored value is decremented by change

            Parameters:
                    player (User): Discord user to adjust force add count of
                    change (int): The amount to decrement allowed force adds by
    '''
    # Want to try and open a file if it's already there
    # NOTE: with clause auto closes the file, so no need to call f.close()
    try:
        with open('stat_tracker.json') as f:
            data = json.load(f)

        data["player_stats"][player.name]["spooky_shillings"] -= change
    
    except:
        print("Error opening stats file!")
    
    try:
        #Now write to file
        with open('stat_tracker.json', 'w') as f:
            json_string = json.dumps(data)
            f.write(json_string)

    except:
        print("Error opening stats file!")

def playerCallOutCount(caller):
    '''
    Return player's current funds for forcing deathrolls

            Parameters:
                    message (Message): The message the caller sent to start a deathroll

            Returns:
                    (int): Total player funds, or 0 if player stats not initialized
    '''
    # Want to try and open a file if it's already there
    # NOTE: with clause auto closes the file, so no need to call f.close()
    try:
        with open('stat_tracker.json') as f:
            data = json.load(f)

        return data["player_stats"][caller.name]["spooky_shillings"]
    except:
        print("Error accessing player stats! Returning 0...")
        return 0

async def gatherCallOuts(message):
    '''
    Gather people mentioned in a discord message that contains the !deathroll command

            Parameters:
                    message (Message): The message the caller sent to start a deathroll

            Returns:
                    players (list): A list of each Discord User that had reacted to the given message
    '''
    return [x for x in message.mentions if x.bot == False]

# Gets list of all emojis owned by server and returns one chosen at random
async def getRandomEmoji(message):
    '''
    Pulls a random emoji from the server

            Parameters:
                    message (list): The message the Bot had sent. This is needed to access the server's info

            Returns:
                    emoji (???): A randomly chosen emoji from the server
    '''
    emojis = message.channel.guild.emojis
    randInd = random.randint(1, int(len(emojis)-1))
    return emojis[randInd]

## Discord-side methods
@client.event
async def on_ready():
    # Just a display message in the console to tell us that our bot is running...
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    # Want to prevent the bot from responding its own messages
    if message.author == client.user:
        return

    # If we get a message from someone that is not the bot, check the message contents
    # If !deathroll is present, we might have a legit call
    if "!deathroll" in message.content.lower():
        # TODO: Create a help call. How do you not have one yet lol

        # NOTE: Formatting as if / elif / else to avoid potential jank of double calls
        #           ie: !deathroll stats titles leaderboard
        #           Above will just do stats instead of all 3
        # If stats is called for, display the stored stats (if any) for the person calling the method
        if "stats" in message.content.lower():
            params = message.content.split()
            # NOTE: Some people have names with spaces. We'll need to do some magic to get around this
            if len(params) > 2:
                stats = pullStats(message, params[2:])
            else:
                stats = pullStats(message)
            await message.channel.send(embed=stats)

        # If titles is called for, display an embed that shows all possible titles and their descriptions
        elif "titles" in message.content.lower():
            titles = displayTitles()
            await message.channel.send(embed=titles)

        # If wager is called for, allow players to place bets on the round
        # TODO: Complete this
        elif "wager" in message.content.lower():
            pass
            #wager, wasRandom = getParams(message)
            #await message.channel.send(embed=titles)
        # If leaderboard is called for, create and show the leaderboard embed
        
        elif "leaderboard" in message.content.lower():
            leaderboard = getLeaderboard()
            await message.channel.send(embed=leaderboard)
        # Otherwise, assume it is a call for a deathroll game
        else:
            global gameOn
            if gameOn:
                await message.channel.send("Game already in progress!")
            else:
                gameOn = True
                try:
                    limit, wasRandom, startDelay, genFail = getParams(message)
                    caller = message.author

                    game = await message.channel.send('Game starts in ' + str(startDelay) + ' seconds! React to this message to join the deathroll!')
                    if genFail:
                        await message.channel.send('Could not read sent in start value! Generating random start instead...')
                    if wasRandom:
                        await message.channel.send('Randomly generated start was ' + str(limit))
                    #await game.add_reaction("<:pesky:822660834534359102>")
                    # NOTE: Below fails on emoji-less servers
                    await game.add_reaction(await getRandomEmoji(game))
                    callOuts = await gatherCallOuts(message)
                    possibleCallOuts = playerCallOutCount(caller)
                    time.sleep(startDelay)
                    # If the deathroll caller is trying to force add people, see if they have the funds to
                    if len(callOuts) > possibleCallOuts:
                        # If they're trying to force more than they have funds to, only look at message reactions
                        if possibleCallOuts > 0:
                            await message.channel.send("You can't force add that many people! You only have " + str(possibleCallOuts) + " call outs!")
                        else:
                            await message.channel.send("You can't force add that many people! You have 0 call outs!")
                        players = await gatherPlayers(game, caller)
                    else:
                         # If they have ample funds, force add all of the callOuts
                         players = await gatherPlayers(game, caller, callOuts)
                         updatePlayerCallOuts(caller, len(callOuts))
                    if len(players) > 1:
                        tracker = setupStatTracking(players, limit, caller)
                        curPlayerInd = 0
                        nRounds = 0
                        while(gameOn):
                            curPlayer = players[curPlayerInd]
                            oldLim = limit
                            limit = roll(limit)
                            nRounds += 1
                            isCrit = False
                            isCut = False
                            isStall = False
                            if limit < (oldLim * 0.05):
                                isCrit = True
                            if limit < (oldLim * 0.35):
                                isCut = True
                            if limit == oldLim:
                                isStall = True
                            if(limit == 1):
                                if nRounds == 1:
                                    endMess = await message.channel.send(curPlayer.name + " rolled a " + str(limit) + " and lost after " + str(nRounds) + " round!")
                                else:
                                    endMess = await message.channel.send(curPlayer.name + " rolled a " + str(limit) + " and lost after " + str(nRounds) + " rounds!")
                                gameOn = False
                                # Update stat tracker
                                updateTracker(tracker, curPlayer, oldLim, limit, nRounds, isCut, isCrit, fin = True)
                                await endMess.add_reaction("🇱")
                            else:
                                roundMessage = await message.channel.send(curPlayer.name + " rolled a " + f"{limit:,}" + "! 3 seconds until next roll!")
                                # If we have a large cut this round, add the scissors emoji
                                # Structured as if / elif so we only get the one reaction per message
                                if isCrit:
                                    await roundMessage.add_reaction("❗")
                                elif isCut:
                                    await roundMessage.add_reaction("✂️")
                                elif isStall:
                                    await roundMessage.add_reaction("<:pesky:822660834534359102>")

                                updateTracker(tracker, curPlayer, oldLim, limit, nRounds, isCut, isCrit)
                                curPlayerInd = (curPlayerInd + 1)%len(players)
                                time.sleep(3)
                        updateTrackerFile(tracker, players)
                    else:
                        await message.channel.send("Starting a game requires more than 1 player!")
                        gameOn = False
                except Exception as e:
                    gameOn = False
                    print(e)


    if "!roll" in message.content:
        # Omega hidden content
        await message.channel.send(roll(10))


# Run the bot
client.run(botKey)