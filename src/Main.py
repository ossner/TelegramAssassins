#Copyright 2020 Sebastian Ossner

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import logging
import emoji
import re
from datetime import datetime
from telegram import (ReplyKeyboardRemove, Bot)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)

from Game import (Game, checkPresent, checkStarted, checkStartable, checkJoinable, startGame, stopGame, underGameLimit, getPlayerlist, playerEnrolled)
from Assassin import (Assassin, checkJoined, getPlayerCodeName, eliminatePlayer)
from DossierGen import compileDossier


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

assassinDetails = {}
GAMECODE, ASSASSINNAME, CODENAME, ADDRESS, MAJOR, PICTURELINK = range(6)


# Fallback command if the user wants to end his
def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Cancelled. Roger')
    return ConversationHandler.END

def new_game(update, context):
    if underGameLimit(update.message.chat_id):
        if not checkPresent(update.message.chat_id):
            game = Game(update.message.chat_id)
            os.mkdir('images\\' + str(game.id))
            os.mkdir('dossiers\\' + str(game.id))
            update.message.reply_text('Alright. You will be the admin of game {}. Give this code to your players so they can register.'
                                        ' You can use /startgame to start this round'.format(game.id))
        else:
            update.message.reply_text('You already have a game registered. You can enter /startgame to start it')
    else:
        update.message.reply_text('You have registered too many past games, contact the developer')

def start_game(update, context):
    if checkPresent(update.message.chat_id):
        if not checkStartable(update.message.chat_id):
            update.message.reply_text('Your recent game has concluded, you can create a new game')
        else:
            if checkStarted(update.message.chat_id):
                update.message.reply_text('Your game has already started')
            else:
                startGame(update.message.chat_id)
                update.message.reply_text('Your game has started and the dossiers will be sent out momentarily')
    else:
        update.message.reply_text('You do not have a game registered, use /newgame to register a game')

def stop_game(update, context):
    if checkPresent(update.message.chat_id):
        if not checkStartable(update.message.chat_id):
            update.message.reply_text('Your recent game has concluded, you can create a new game')
        else:
            if checkStarted(update.message.chat_id):
                stopGame(update.message.chat_id)
                update.message.reply_text('Your game has concluded and the players will be notified. Here is the leaderboard')
            else:
                update.message.reply_text('Your game did not start yet. You can start it using the /startgame command')
    else:
        update.message.reply_text('You do not have a game registered, use /newgame to register a game')

# Texts message to all players enrolled in game
def broadcast(update, context):
    if checkPresent and checkStarted:
        message = ' '.join(context.args)
        players = getPlayerlist(update.message.chat_id)
        for player in players:
            context.bot.send_message(player[0], "Assassin! Your gamemaster has a message for you:\n" + message)
        update.message.reply_text('Your message has been forwarded to the players')
    else:
        update.message.reply_text('You don\'t have a running game at the moment')


def join_game(update, context):
    if checkJoined(update.message.chat_id):
        # TODO: If player is enrolled in a stopped game and not in a running game, simply update gameID and give player the chance to drop out if new signup is desired
        update.message.reply_text('You are already enrolled in a running game. You can use /dropout to cancel that')
        return ConversationHandler.END
    else:
        update.message.reply_text('Alright. Please tell me the super secret 6-digit code for the game')
        return GAMECODE

def assassin_name(update, context):
    assassinDetails['gameId'] = update.message.text;
    if re.match(r"\d{6}", assassinDetails['gameId']) and checkJoinable(update.message.text):
        update.message.reply_text('Got it, now please provide me with your full name')
        return ASSASSINNAME
    else:
        update.message.reply_text('This game does not exist or is not joinable anymore')
        return ConversationHandler.END

def code_name(update, context):
    assassinDetails['name'] = update.message.text;
    if dirty(assassinDetails['name']):
        update.message.reply_text('🚨 Possible breach detected 🚨\n Please start over and refrain from using special characters')
        return ConversationHandler.END
    else:
        update.message.reply_text('Ok. Now tell me your way more interesting codename'.format(assassinDetails['name']))
        return CODENAME

def address(update, context):
    assassinDetails['codeName'] = update.message.text;
    if dirty(assassinDetails['codeName']):
        update.message.reply_text('🚨 Possible breach detected 🚨\n Please start over and refrain from using special characters')
        return ConversationHandler.END
    else:
        update.message.reply_text('Affirmative {}. We also need your address for the life insurance form'.format(assassinDetails['codeName']))
        return ADDRESS

def major(update, context):
    assassinDetails['address'] = update.message.text
    if dirty(assassinDetails['address']):
        update.message.reply_text('🚨 Possible breach detected 🚨\n Please start over and refrain from using special characters')
        return ConversationHandler.END
    else:
        update.message.reply_text('Almost done. Now I need to know your major')
        return MAJOR

def image(update, context):
    assassinDetails['major'] = update.message.text
    if dirty(assassinDetails['major']):
        update.message.reply_text('🚨 Possible breach detected 🚨\n Please start over and refrain from using special characters')
        return ConversationHandler.END
    else:
        update.message.reply_text('Lastly I need your pretty picture for your dossier')
        return PICTURELINK

def signupDone(update, context):
    photo_file = update.message.photo[-1].get_file()
    chatId = update.message.chat_id
    photo_file.download('images\\' + str(assassinDetails['gameId']) + '\\' + str(chatId) + '.jpg')

    player = Assassin(assassinDetails['name'], assassinDetails['codeName'], assassinDetails['address'], chatId, assassinDetails['major'], assassinDetails['gameId'])

    update.message.reply_text('That\'s it. I will contact you again once the game has begun. Stay vigilant!')

    compileDossier(player)

def dropout(update, context):
    if checkJoined(update.message.chat_id):
        update.message.reply_text('You are hereby terminated')
        eliminatePlayer(update.message.chat_id)
    else:
        update.message.reply_text('You are not enrolled in a running game')

def burn(update, context):
    player = context.args[0]
    if re.match(r"^\d+$", player):
        if playerEnrolled(player, update.message.chat_id):
            update.message.reply_text('Burning player ' + getPlayerCodeName(player, update.message.chat_id)[0])
            eliminatePlayer(player)
        else:
            update.message.reply_text('This player is not enrolled in your game')
    else:
        update.message.reply_text('This is not a valid player-id')
    pass

def help_overview(update, context):
    update.message.reply_text(
        'This Bot was written by github.com/ossner. The code is licensed under the MIT license\n'
        '/help - Get an overview of the available commands\n'
        '/joingame - Join an upcoming game\n'
        '/dropout - Drop out of the game you\'re registered to\n'
        '/newgame - Create a new game of Assassins where you\'re the admin\n'
        '/info - Get information about the game you\'re in\n'
        '/confirmkill - Confirm target elimination\n'
        '/dossier - Re-send your target\'s information\n'
        '/scoreboard - [ADMIN] Get the scoreboard of the game you\'re running\n'
        '/broadcast - [ADMIN] Send a message to all participating players\n'
        '/burn - [ADMIN] Burn an assassin after non-compliance to the rules')

def dirty(string):
    # TODO: test if this filters naughty stuff
    return re.compile('[@!#$%^&*<>?\|}{~:;]').search(string) or bool(emoji.get_emoji_regexp().search(string))

def main():
    updater = Updater(os.getenv("SAS_TOKEN"), use_context=True)
    dp = updater.dispatcher
    newGameHandler = CommandHandler('newgame', new_game, run_async=True)
    dp.add_handler(newGameHandler)

    startgame_handler = CommandHandler('startgame', start_game, run_async=True)
    dp.add_handler(startgame_handler)

    stopgame_handler = CommandHandler('stopgame', stop_game, run_async=True)
    dp.add_handler(stopgame_handler)

    broadcast_handler = CommandHandler('broadcast', broadcast, run_async=True)
    dp.add_handler(broadcast_handler)

    joinGame_handler = ConversationHandler(entry_points=[CommandHandler('joinGame', join_game, run_async=True)],
                                          states={
                                              # After getting key, you move into method in the value
                                              GAMECODE: [MessageHandler(Filters.text, assassin_name, run_async=True)],
                                              ASSASSINNAME: [MessageHandler(Filters.text, code_name, run_async=True)],
                                              CODENAME: [MessageHandler(Filters.text, address, run_async=True)],
                                              ADDRESS: [MessageHandler(Filters.text, major, run_async=True)],
                                              MAJOR: [MessageHandler(Filters.text, image, run_async=True)],
                                              PICTURELINK: [MessageHandler(Filters.photo, signupDone, run_async=True)]
                                          },
                                          fallbacks=[CommandHandler('cancel', cancel)])
    dp.add_handler(joinGame_handler)

    dropout_handler = CommandHandler('dropout', dropout, run_async=True)
    dp.add_handler(dropout_handler)

    burn_handler = CommandHandler('burn', burn, run_async=True)
    dp.add_handler(burn_handler)

    #TODO: Leaderboard, ConfirmKill, ConfirmDead, Dossier

    help_handler = CommandHandler('help', help_overview, run_async=True)
    dp.add_handler(help_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
