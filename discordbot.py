import discord
from eclipse import *
import re
from discord.ext import commands

TOKEN = "ODUyOTI3MDE0ODY4MzUzMDc0.YMN8Lg.gAyquxemQWzL1-PRvlymqYraIOA"



intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):

    if message.author == client.user: # do not respond to yourself
        return

    if (message.content).startswith('-battle '):

        if (re.search(r".*help.*", message.content)!=None):
            response = "This is a battle calculator for Eclipse, use it with command:\n"
            response+= "> -battle attship1 + attship2 VS defship1 + defship2\n"
            response+= "(with any number of ships on each side). Each ship is written:\n"
            response+= "> number type initiative hull computer shield canons missiles.\n"
            response+= "Type = int, cru, dre, sba or npc. Canons are written as a list of letters, one letter per die, **y**ellow, **o**range, **b**lue, **r**ed, **p**ink. Misiles are the same but starting with letter **m**. "
            response+= "Example:\n> 5 int 4 3 2 1 yyyyyoooobbbrrp myyyyooobbr\n means 5 interceptors with 4 initiative, 3 hull, 2 computer, 1 shield, 5 yellow canons, 4 orange canons, 3 blue canons, 2 red canon and 1 pink canon, 4 yellow missiles, 3 orange missiles, 2 blue missiles and 1 red missile"
            await message.channel.send(response)
            return
        
        argument = message.content[len('-battle'):]
        sides = argument.split('VS')

        ship_list_list = []
        for side in sides:
            ships = side.split('+')
            ship_list = []
            for ship in ships:
                print (ship)
                regex = re.search(r"(\d+) (int|cru|dre|sba|npc) (\d+) (\d+) (\d+) (\d+)?(.*)", ship)
                weapons = regex[7].split ('m')
                canons = [weapons[0].count('y'), weapons[0].count('o'), weapons[0].count('b'), weapons[0].count('r'), weapons[0].count('p')]
                if (len(weapons)==2):
                    missis = [weapons[1].count('y'), weapons[1].count('o'), weapons[1].count('b'), weapons[1].count('r'), weapons[1].count('p')]
                else:
                    missis = [0,0,0,0,0]
                ship = Ship(regex[2], int(regex[1]), int(regex[3]), int(regex[4]), int(regex[5]), int(regex[6]), canons, missis)
                ship_list.append(ship)
            ship_list_list.append(ship_list)
        

        test = BattleWinChances (ship_list_list[0], ship_list_list[1], remaining_ships=True)

        await message.channel.send("Chance of attacker winning: " + "{:.2%}".format(test.win_chance) )
        await message.channel.send(file=discord.File('battle.jpg'))
        

    
    return

        
client.run(TOKEN)