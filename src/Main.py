# -*- coding: utf-8 -*-
# Copyright 2020 Sebastian Ossner

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import logging
import emoji
import re
import random
import html
import json
import traceback
from telegram import (ParseMode, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler)
from telegram.error import (TelegramError, Unauthorized, BadRequest, 
                            TimedOut, ChatMigrated, NetworkError)

from Game import (Game, checkPresent, checkJoinable, startGame, stopGame, getPlayerlist, playerEnrolled, getMaster)
from Assassin import (Assassin, checkJoined, getPlayerCodeName, eliminatePlayer, checkAlive, setPresumedDead, getAssassin, getPresumedDead, reconnect)


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

GAMECODE, ASSASSINNAME, CODENAME, WEAPON, ADDRESS, MAJOR, PICTURE = range(7)

def error_handler(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    message = (
        'An exception was raised while handling an update\n'
        '<pre>update = {}</pre>\n\n'
        '<pre>context.chat_data = {}</pre>\n\n'
        '<pre>context.user_data = {}</pre>\n\n'
        '<pre>{}</pre>'
    ).format(
        html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False)),
        html.escape(str(context.chat_data)),
        html.escape(str(context.user_data)),
        html.escape(tb_string),
    )
    context.bot.send_message(chat_id=705347597, text=message, parse_mode=ParseMode.HTML)
    update.message.reply_text('An error occured, please try again')
    reconnect()
def cancel(update, context):
    user = update.message.from_user
    logger.info('User name: {x}, id: {y} cancelled the conversation.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
    update.message.reply_text('Cancelled. Roger')
    return ConversationHandler.END

def start(update, context):
    update.message.reply_text('Greetings aspiring assassin!\nI am M, your contact into the Secret Assassins Society. If you want to join a game of Assassins, type /joingame, if you want to start one yourself, type /newgame.\nIf you want to know more about me and what I can do, type /help')

def new_game(update, context):
    logger.info('User name: {x}, id: {y} created a new game.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
    # If the user has a telegram username registered
    if update.message.from_user['username']:
        # If the user already has a game (either registered or started)
        if checkPresent(update.message.chat_id):
            if checkPresent(update.message.chat_id, started=True):
                update.message.reply_text('Your game has already started')
            else:
                update.message.reply_text('You already have a game registered. You can enter /startgame to start it')
        else:
            # Create database entry for game
            game = Game(update.message.chat_id, update.message.from_user['username'])
            # create directory for storing game information
            os.mkdir('images/' + str(game.id))
            update.message.reply_text(
                'Alright. You will be the admin of game {}. Give this code to your players so they can register.\n'
                'You can use /startgame to start this round'.format(game.id))
    else:
        update.message.reply_text('You don\'t have a telegram username, please create one on your profile so your assassins can text you')

def start_game(update, context):
    logger.info('User name: {x}, id: {y} started their game.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
    if checkPresent(update.message.chat_id):
        if checkPresent(update.message.chat_id, started=True):
            update.message.reply_text('Your game has already started')
        else:
            update.message.reply_text('Your game has started and the dossiers will be sent out momentarily')
            players = startGame(update.message.chat_id)
            # Notify players and start the game
            for player in players:
                context.bot.send_message(player[0], 'Greetings assassin!\nYour game master has started the game and you have been assigned your first target:')
                sendTarget(context, player[0])
    else:
        update.message.reply_text('You do not have a game registered, use /newgame to register a game')

def stop_game(update, context):
    logger.info('User name: {x}, id: {y} stopped their game.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
    if checkPresent(update.message.chat_id):
        if checkPresent(update.message.chat_id, started=True):
            update.message.reply_text('Your game has concluded and the players will be notified. Here is the leaderboard')
            leaderboard(update, context)
            stopGame(update.message.chat_id)
        else:
            update.message.reply_text('Your game did not start yet. You can start it using the /startgame command')
    else:
        update.message.reply_text('You do not have a game registered, use /newgame to register a game')

# Texts message to all players enrolled in game
def broadcast(update, context):
    if checkPresent(update.message.chat_id):
        if not context.args:
            update.message.reply_text('You cannot send an empty message!')
        else:
            message = ' '.join(context.args)
            logger.info('User name: {x}, id: {y} broadcasted \"{z}\"'.format(x=update.message.from_user.first_name, y=update.message.chat_id, z=message))
            players = getPlayerlist(update.message.chat_id)
            for player in players:
                context.bot.send_message(player[0], "Assassin! Your gamemaster has a message for you:\n" + message)
            update.message.reply_text('Your message has been forwarded to the players')
    else:
        update.message.reply_text('You don\'t have a running game at the moment')

def join_game(update, context):
    logger.info('User name: {x}, id: {y} tried to join a game.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
    if checkJoined(update.message.chat_id):
        update.message.reply_text('You are already enrolled in a running game. You can use /dropout to cancel that')
        return ConversationHandler.END
    else:
        update.message.reply_text('If at any point you want to stop the sign-up process, simply type /cancel')
        update.message.reply_text('Alright. Please tell me the super secret 6-digit code for the game')
        return GAMECODE

def assassin_name(update, context):
    context.user_data['gameId'] = update.message.text
    if re.match(r"\d{6}", context.user_data['gameId']) and checkJoinable(update.message.text):
        update.message.reply_text('Got it, now please provide me with your full name')
        return ASSASSINNAME
    else:
        update.message.reply_text('This game does not exist or is not joinable anymore')
        return ConversationHandler.END

def code_name(update, context):
    context.user_data['name'] = update.message.text;
    if dirty(context.user_data['name']):
        update.message.reply_text('🚨 Possible breach detected 🚨\nPlease start over and refrain from using special characters')
        return ConversationHandler.END
    else:
        update.message.reply_text('Ok. Now tell me your way more interesting codename'.format(context.user_data['name']))
        return CODENAME

def weapon(update, context):
    context.user_data['codeName'] = update.message.text;
    if dirty(context.user_data['codeName']):
        update.message.reply_text('🚨 Possible breach detected 🚨\nPlease start over and refrain from using special characters')
        return ConversationHandler.END
    
    keyboard = [
        [
            InlineKeyboardButton('I need a weapon', callback_data=1),
            InlineKeyboardButton('I have a weapon', callback_data=0)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('To participate it is recommended that you own a hydro-pneumatic weapon. Our waterarms department can provide you with one if needed.', reply_markup=reply_markup)
    return WEAPON

def address(update, context):
    query = update.callback_query
    query.answer()
    context.user_data['weapon'] = query.data
    query.edit_message_text('Affirmative {}. We also need your address for the life insurance form'.format(context.user_data['codeName']))
    return ADDRESS

def major(update, context):
    context.user_data['address'] = update.message.text
    if dirty(context.user_data['address']):
        update.message.reply_text('🚨 Possible breach detected 🚨\nPlease start over and refrain from using special characters')
        return ConversationHandler.END
    else:
        update.message.reply_text('Almost done. Now I need to know your major')
        return MAJOR

def image(update, context):
    context.user_data['major'] = update.message.text
    if dirty(context.user_data['major']):
        update.message.reply_text('🚨 Possible breach detected 🚨\nPlease start over and refrain from using special characters')
        return ConversationHandler.END
    else:
        update.message.reply_text('Lastly I need your pretty picture for your dossier')
        return PICTURE

def signup_done(update, context):
    photo_file = update.message.photo[-1].get_file()
    chatId = update.message.chat_id
    photo_file.download('images/{}/{}.jpg'.format(str(context.user_data['gameId']), str(chatId)))
    if checkJoinable(context.user_data['gameId']):
        player = Assassin(context.user_data['name'], context.user_data['codeName'], context.user_data['address'], chatId, context.user_data['major'], context.user_data['weapon'], context.user_data['gameId'])
        update.message.reply_text('That\'s it. I will contact you again once the game has begun. Stay vigilant!')
        logger.info('User name: {x}, id: {y} finished signing up for a game.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
    else:
        update.message.reply_text('Could not finish signup as game has already started')
    return ConversationHandler.END

def dropout(update, context):
    logger.info('User name: {x}, id: {y} request timed out.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
    if checkJoined(update.message.chat_id):
        if checkJoined(update.message.chat_id, started=True):
            if checkAlive(update.message.chat_id):
                update.message.reply_text('You are hereby terminated')
                hunter = eliminatePlayer(update.message.chat_id)
                sendTarget(context, hunter[0])
            else:
                update.message.reply_text('You are already dead, but the game is still running. We are unable to fully terminate you until the game has concluded')
        else:
            eliminatePlayer(update.message.chat_id)
            update.message.reply_text('You are hereby terminated')
    else:
        update.message.reply_text('You are not enrolled in a game')

def burn(update, context):
    # If the person has a game registered
    if checkPresent(update.message.chat_id):
        # If there is a player id provided in the message
        if context.args:
            player = context.args[0]
            # If the player id argument actually consists of digits
            if re.match(r"^\d+$", player):
                # If the player id is enrolled in the game of the master
                if playerEnrolled(player, update.message.chat_id):
                    context.bot.send_message(player, 'You have been burnt by the game master. You are therefore considered dead')
                    update.message.reply_text('Burning player ' + getPlayerCodeName(player, update.message.chat_id)[0])
                    # If the game started, it will return the hunter of the burnt player
                    hunter = eliminatePlayer(player)
                    # if there is a result returned, the target of the burnt players hunter was updated
                    if hunter:
                        sendTarget(context, hunter[0])
                else:
                    update.message.reply_text('This player is not enrolled in your game. Use /players to get an overview of your players and their ids')
            else:
                update.message.reply_text('This is not a valid player-id. Use /players to get an overview of your players and their ids')
        else:
            update.message.reply_text('Please provide the disgraced assassins id after the command (e.g. /burn 123456789), use /players to obtain a list')
    else:
        update.message.reply_text('You do not have a game registered')

def dossier(update, context):
    if (checkJoined(update.message.chat_id, started=True)):
    logger.info('User name: {x}, id: {y} request timed out.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
        sendTarget(context, update.message.chat_id)
    else:
        update.message.reply_text('You are not enrolled in a running game')

def sendTarget(context, chat_id):
    target = getAssassin(getAssassin(chat_id)[6])
    # If the target and the hunter are the same person, the game is over
    if chat_id == target[0]:
        # Index 8 is game id
        winner(context, target[8], chat_id)
        return
    random_skills = ['lockpicking', 'hand-to-hand combat', 'target acquisition',
                'covert operations', 'intelligence gathering', 'marksmanship',
                'knife-throwing', 'explosives', 'poison', 'seduction',
                'disguises', 'exotic weaponry', 'vehicles', 'disguise']
    rand = random.randint(0, len(random_skills) - 1)
    rand2 = random.randint(0, len(random_skills) - 1)
    while rand == rand2:
        rand2 = random.randint(0, len(random_skills) - 1)
    
    context.bot.send_photo(chat_id, photo=open('images/' + str(target[8]) + '/' + str(target[0]) + '.jpg', 'rb'), caption=
    'Name: ' + str(target[1]) + 
    '\n\nCodename: ' + str(target[2]) + 
    '\n\nAddress: ' + str(target[3]) + 
    '\n\nSpeciality: ' + random_skills[rand]+', '+random_skills[rand2]+', '+str(target[4])+ 
    '\n\nConsidered to be armed and extremely dangerous!')

def winner(context, game_id, chat_id):
    context.bot.send_message(chat_id, 'Congratulations Assassin. You are the last person standing in your game! You truly are an exceptional killer.')
    gameMaster = getMaster(game_id)[0]
    context.bot.send_message(gameMaster, 'Your game has concluded! There is only one person left standing.')
    send_leaderboard(context, gameMaster)
    stopGame(gameMaster)

def leaderboard(update, context):
    if checkPresent(update.message.chat_id):
        if checkPresent(update.message.chat_id, started=True):
            send_leaderboard(context, update.message.chat_id)
        else:
            update.message.reply_text('Your game has not started yet. Use /startgame to start it')
    else:
        update.message.reply_text('You do not have a game registered, use /newgame to register a game')

def send_leaderboard(context, chat_id):
    table = '`Name [X] = dead' + (' ' * 7) + '| Codename' + (' ' * 4) + '| Kills\n'
    players = getPlayerlist(chat_id)
    for player in players:
        if player[4]:
            table += player[1] + (' ' * 8)[:8-len([1])] + '| ' + player[2] + (' ' * 12)[:12-len(player[2])] + '| ' + str(player[3]) + '\n'
        else:
            table += player[1] + ' [X]' + (' ' * 4)[:4-len([1])] + '| ' + player[2] + (' ' * 12)[:12-len(player[2])] + '| ' + str(player[3]) + '\n'
    context.bot.send_message(chat_id, text=table + '`', parse_mode=ParseMode.MARKDOWN)

def players(update, context):
    if checkPresent(update.message.chat_id):
        table = '`Id' + (' ' * 8) + '| Name' + (' ' * 16) + '| Codename\n'
        players = getPlayerlist(update.message.chat_id)
        for player in players:
            table += str(player[0]) + (' ' * 10)[:10-len(str(player[0]))] + '| ' + player[1] + (' ' * 10)[:10-len(player[1])] + '| ' + player[2] + '\n'
        update.message.reply_text(text=table + '`', parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text('You do not have a game registered, use /newgame to register a game')

# Player claims to have killed their target, send confirmation request to target, which can be contested
def confirmKill(update, context):
    # extracts information about target of this player
    target = getAssassin(getAssassin(update.message.chat_id)[6])
    # index 0 is player id
    setPresumedDead(target[0], 1)
    context.bot.send_message(target[0], 'Your hunter has claimed to have assassinated you! If this is true, type /confirmdead. If it is not, text your game master @{}'.format(getMaster(target[8])[1]))

def confirmDead(update, context):
    if getPresumedDead(update.message.chat_id):
        update.message.reply_text('I guess this is only natural selection')
        hunter = eliminatePlayer(update.message.chat_id, kill=True)
        if hunter:
            sendTarget(context, hunter[0])
    else:
        update.message.reply_text('There is nothing to contest')

def rules(update, context):
    pass

def help_overview(update, context):
    logger.info('User name: {x}, id: {y} requested help.'.format(x=update.message.from_user.first_name, y=update.message.chat_id))
    update.message.reply_text(
        'This Bot was written by github.com/ossner. The code is licensed under the MIT license\n\n'
        '*User commands:*\n'
        '/help - Get an overview of the available commands\n'
        '/rules - Get an overview of the rules for the game (subject to change)\n'
        '/joingame - Join an upcoming game\n'
        '/dropout - Drop out of the game you\'re registered to\n'
        '/newgame - Create a new game of Assassins where you\'re the admin\n'
        '/confirmkill - Confirm target elimination\n'
        '/dossier - Re-send your target\'s information\n\n'
        '*Admin commands:*\n'
        '/leaderboard - Get the scoreboard of the game you\'re hosting\n'
        '/broadcast - Send a message to all participating players\n'
        '/burn - Burn an assassin after non-compliance to the rules', parse_mode=ParseMode.MARKDOWN)

def dirty(string):
    return re.compile('[@!#$%^&*<>?\|}{~:;]').search(string) or bool(emoji.get_emoji_regexp().search(string))

def main():
    updater = Updater(os.getenv("SAS_TOKEN"), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start, run_async=True))

    dp.add_handler(CommandHandler('newgame', new_game, run_async=True))

    dp.add_handler(CommandHandler('startgame', start_game, run_async=True))

    dp.add_handler(CommandHandler('stopgame', stop_game, run_async=True))

    dp.add_handler(CommandHandler('broadcast', broadcast, run_async=True))

    joinGame_handler = ConversationHandler(
        entry_points=[CommandHandler('joinGame', join_game, run_async=True)],
        states={
            # After getting key, you move into method in the value
            GAMECODE: [MessageHandler(Filters.text & ~Filters.command, assassin_name, run_async=True)],
            ASSASSINNAME: [MessageHandler(Filters.text & ~Filters.command, code_name, run_async=True)],
            CODENAME: [MessageHandler(Filters.text & ~Filters.command, weapon, run_async=True)],
            WEAPON: [CallbackQueryHandler(address, pattern='^\d$' , run_async=True)],
            ADDRESS: [MessageHandler(Filters.text & ~Filters.command, major, run_async=True)],
            MAJOR: [MessageHandler(Filters.text & ~Filters.command, image, run_async=True)],
            PICTURE: [MessageHandler(Filters.photo & ~Filters.command, signup_done, run_async=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)])
    dp.add_handler(joinGame_handler)

    dp.add_handler(CommandHandler('dropout', dropout, run_async=True))

    dp.add_handler(CommandHandler('burn', burn, run_async=True))

    dp.add_handler(CommandHandler('dossier', dossier, run_async=True))

    dp.add_handler(CommandHandler('leaderboard', leaderboard, run_async=True))

    dp.add_handler(CommandHandler('players', players, run_async=True))

    dp.add_handler(CommandHandler('confirmKill', confirmKill, run_async=True))

    dp.add_handler(CommandHandler('confirmDead', confirmDead, run_async=True))

    dp.add_handler(CommandHandler('rules', rules, run_async=True))

    dp.add_handler(CommandHandler('help', help_overview, run_async=True))

    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
