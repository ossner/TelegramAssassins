# -*- coding: utf-8 -*-

import os
import logging
import re
import html
import random
import json
import traceback
from telegram import (ParseMode, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler)
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
import sqlite3
import os
from pathlib import Path

from AssassinsApp.bot_database_interface import get_developers, add_game, user_has_game, db_start_game, game_started, \
    check_joined, get_master, add_assassin, game_exists, kill_player, remove_player, get_target_of, get_assassin_ids, \
    assign_targets, get_game_id

BASE_DIR = Path(__file__).resolve().parent.parent

GAMECODE, ASSASSINNAME, CODENAME, WEAPON, ADDRESS, MAJOR, PICTURE = range(7)  # Constants needed for conversation

ANSWER, MESSAGE = 1, 2  # Constant for the task conversation, since there is only one step

# Enable logging
logging.basicConfig(filename='bot.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


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
    for admin in get_developers():
        context.bot.send_message(chat_id=admin, text=message, parse_mode=ParseMode.HTML)
    update.message.reply_text('An error occurred, please try again. If the issue persists, text @ossner')


def start(update, context):
    """ Welcome message for new users, command has to be entered at the start of every new conversation """
    logger.info('User name: {x}, id: {y} started the chat.'.format(x=update.message.from_user.first_name,
                                                                   y=update.message.chat_id))
    update.message.reply_text(
        'Greetings aspiring assassin!\nI am M, your contact into the Secret Assassins Society. If you want to join a '
        'game of Assassins, type /joingame, if you want to start one yourself, type /newgame.\nIf you want to know '
        'more about me and what I can do, type /help')


def cancel(update, context):
    """ Fallback command if the user cancels the conversation """
    logger.info('User name: {x}, id: {y} cancelled the conversation.'.format(x=update.message.from_user.first_name,
                                                                             y=update.message.chat_id))
    update.message.reply_text('Cancelled. Roger.')
    return ConversationHandler.END


def new_game(update, context):
    logger.info('User name: {x}, id: {y} created a new game.'.format(x=update.message.from_user.first_name,
                                                                     y=update.message.chat_id))
    # If the user has a telegram username registered
    if update.message.from_user['username']:
        # If the user already has a game (either registered or started)
        game_id = random.randint(100, 999)
        if add_game(game_id, update.message.chat_id, update.message.from_user['username']):
            # create directory for storing game information
            os.mkdir(os.path.join('images', str(game_id)))
            update.message.reply_text(
                'Alright. You will be the admin of game {}. Give this number to your players so they can register.\n'
                'You can use /startgame to start this round'.format(game_id))
        else:
            update.message.reply_text('You already have a game registered.')
    else:
        update.message.reply_text(
            'You don\'t have a telegram username, please create one on your profile so your assassins can text you')


def start_game(update, context):
    """ Start the game of the person issuing the command

    This includes setting the game started value to 1,
    computing the player's targets and sending out the
    dossiers
    """
    logger.info('User name: {x}, id: {y} tried to start their game.'.format(x=update.message.from_user.first_name,
                                                                            y=update.message.chat_id))
    if user_has_game(update.message.chat_id):
        game_id = get_game_id(game_master_id=update.message.chat_id)
        if not game_started(game_id):
            logger.info('User name: {x}, id: {y} started their game.'.format(x=update.message.from_user.first_name,
                                                                             y=update.message.chat_id))
            db_start_game(game_id)
            update.message.reply_text('Your game has been started and your assassins will be notified')
            assign_targets(game_id)
            for assassin in get_assassin_ids(game_id):
                send_target(context, assassin)
        else:
            update.message.reply_text('Your game has already started')
    else:
        update.message.reply_text('You don\'t have a game registered, use /newgame to create one')


def stop_game(update, context):
    """ This command stops the game of the person issuing it

    This means the game has to have been stopped manually, so there was no
    last man standing. Before the game is stopped in the database, compute the leaderboard
    and determine the players with:
    1. The most kills (alive)
    2. The most kills (dead if more kills than alive)
    """
    if user_has_game(update.message.chat_id):
        if game_started(get_game_id(game_master_id=update.message.chat_id)):
            logger.info('User name: {x}, id: {y} stopped their game.'.format(x=update.message.from_user.first_name,
                                                                             y=update.message.chat_id))
            pass
            # TODO send leaderboard, stop game
        else:
            update.message.reply_text('Your game has not started yet, use /startgame to start it')
    else:
        update.message.reply_text('You do not have a game registered. Create one with /newgame')


def broadcast(update, context, only_alive=True):
    """ Send a message to all the users participating in the game

    if only_alive is False then it will send the update out to all the users
    registered in the game. If True (default) it will only send the message
    to the players alive
    """
    if user_has_game(update.message.chat_id):
        if context.args:
            message = ' '.join(context.args)
            logger.info('User name: {x}, id: {y} broadcast {z}.'.format(x=update.message.from_user.first_name,
                                                                        y=update.message.chat_id,
                                                                        z=message))
            players = get_assassin_ids(get_game_id(update.message.chat_id), only_alive=only_alive)
            for player in players:
                try:
                    context.bot.send_message(player, message)
                except:
                    logger.warning('User {} could not be contacted', player)
            update.message.reply_text('Your message has been forwarded to {} players'.format(len(players)))
        else:
            update.message.reply_text('You can\'t send an empty message')
    else:
        update.message.reply_text('You don\'t have a game registered')


def broadcast_all(update, context):
    """ Let's a game master send a message to all the players (alive or dead) """
    broadcast(update, context, only_alive=False)


def join_game(update, context):
    """ Start the sign-up process for users to join an existing game """
    if check_joined(update.message.chat_id):
        update.message.reply_text('You are already enrolled in a running game. You can use /dropout to cancel that')
        return ConversationHandler.END
    else:
        update.message.reply_text(
            'Privacy Notice: Please note that the information you provide us with will be sent to other '
            'people participating in the game. No data will be shared with people outside of the game '
            'and all data will be permanently deleted once the game is over. If you have any objections to this, '
            'please text @ossner')
        update.message.reply_text('If something stops working, text @ossner. If at any point you want to stop the '
                                  'sign-up process, simply type /cancel')
        update.message.reply_text('Alright. Please tell me the super secret 3-digit code for the game')
        return GAMECODE


def get_assassin_name(update, context):
    logger.info('User name: {x}, id: {y} started signing up for a game.'.format(x=update.message.from_user.first_name,
                                                                                y=update.message.chat_id))
    if re.match(r"^\d+$", update.message.text):
        context.user_data['game_id'] = int(update.message.text)
        if not game_started(game_id=update.message.text) and game_exists(game_id=update.message.text):
            update.message.reply_text('Got it, now please provide me with your full name')
            return ASSASSINNAME
        else:
            update.message.reply_text('This game does not exist or is not joinable anymore, please try again')
            return GAMECODE
    else:
        update.message.reply_text('This is not a valid gameId')
        return ConversationHandler.END


def get_code_name(update, context):
    context.user_data['name'] = update.message.text
    if dirty(context.user_data['name']):
        update.message.reply_text('🚨 Possible breach detected 🚨\nPlease refrain from using special characters')
    else:
        update.message.reply_text(
            'Ok. Now tell me your way more interesting codename'.format(context.user_data['name']))
        return CODENAME


def check_needs_weapon(update, context):
    context.user_data['code_name'] = update.message.text
    if dirty(context.user_data['code_name']):
        update.message.reply_text('🚨 Possible breach detected 🚨\nPlease refrain from using special characters')

    keyboard = [
        [
            InlineKeyboardButton('I need a weapon', callback_data=1),
            InlineKeyboardButton('I have a weapon', callback_data=0)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        'To participate it is recommended that you own a hydro-pneumatic weapon 🔫. Such weapons will be handed out by '
        'our specialists. We can not guarantee you will receive one though.',
        reply_markup=reply_markup)
    return WEAPON


def get_address(update, context):
    query = update.callback_query
    query.answer()
    context.user_data['weapon'] = query.data
    query.edit_message_text(
        'Affirmative {}. We also need your address for the life insurance form (Street and Apt. #)'.format(
            context.user_data['code_name']))
    return ADDRESS


def get_major(update, context):
    context.user_data['address'] = update.message.text
    if dirty(context.user_data['address']):
        update.message.reply_text('🚨 Possible breach detected 🚨\nPlease refrain from using special characters')
    else:
        update.message.reply_text('Almost done. Now I need to know what you study')
        return MAJOR


def get_image(update, context):
    context.user_data['major'] = update.message.text
    if dirty(context.user_data['major']):
        update.message.reply_text('🚨 Possible breach detected 🚨\nPlease refrain from using special characters')
        return ConversationHandler.END
    else:
        update.message.reply_text('Lastly I need your pretty picture for your dossier')
        return PICTURE


def signup_done(update, context):
    try:
        photo_file = update.message.photo[-1].get_file()
    except IndexError:
        update.message.reply_text('Could not process picture, please try again')
        return PICTURE
    chat_id = update.message.chat_id
    if not game_started(game_id=context.user_data['game_id']):
        if add_assassin(chat_id, context.user_data['name'], context.user_data['code_name'],
                        context.user_data['address'], context.user_data['major'], context.user_data['weapon'],
                        context.user_data['game_id']):
            photo_file.download('images/{}/{}.jpg'.format(context.user_data['game_id'], str(chat_id)))
            update.message.reply_text(get_rules())
            update.message.reply_text(
                'That\'s it. I will contact you again once the game has begun. Stay vigilant! If you have any further '
                'questions, text your game master @{}'.format(
                    get_master(context.user_data['game_id'])))
            logger.info(
                'User name: {x}, id: {y} finished signing up for a game.'.format(x=update.message.from_user.first_name,
                                                                                 y=update.message.chat_id))
        else:
            update.message.reply_text('An error occurred, please try the sign-up again')
    else:
        update.message.reply_text('Could not finish signup as game has already started')
    return ConversationHandler.END


def dropout(update, context):
    """ User wants to drop out of a game, notify hunter and update database

    If an assassin wants to leave a running game, kill them off without attributing a kill
    to their hunter and then notify the hunter about their new target.
    If the game has not started yet, simply remove the player from the database
    """
    if check_joined(update.message.chat_id):
        logger.info('User name: {x}, id: {y} dropped out of a game.'.format(x=update.message.from_user.first_name,
                                                                            y=update.message.chat_id))
        if game_started(get_game_id(participant_id=update.message.chat_id)):
            kill_player(update.message.chat_id)  # The game has started, so kill the player without attributing points
        else:
            remove_player(update.message.chat_id)  # The game has not yet started, the user can just be removed
        update.message.reply_text('You took the coward\'s way out')
    else:
        update.message.reply_text('You are not enrolled in a game')


def burn(update, context):
    """ Forcefully removes a player from the game

    A game master can invoke this command to remove a player
    that has violated the rules from the game.
    This needs to kill off the player in the database and
    if the game has started, notify their hunter about the
    new target.
    """
    #  Check if calling user has a game associated with them
    if game_exists(get_game_id(update.message.chat_id)):
        #  Check command args validity
        if context.args and re.match(r"^\d+$", context.args[0]):
            player_id = context.args[0]
            #  Check if player is actually enrolled in this persons game TODO remove and handle with db
            if get_game_id(game_master_id=update.message.chat_id) == get_game_id(participant_id=player_id):
                kill_player(player_id)
            else:
                update.message.reply_text('This assassins is not enrolled in your game')
        else:
            update.message.reply_text('Specified player id is invalid')
    else:
        update.message.reply_text('You do not have a game registered')


def dossier(update, context):
    """ User requested their target's dossier, send all the needed information """
    if check_joined(update.message.chat_id):
        if game_started(get_game_id(participant_id=update.message.chat_id)):
            logger.info('User name: {x}, id: {y} requested their dossier.'.format(x=update.message.from_user.first_name,
                                                                                  y=update.message.chat_id))
            send_target(context, update.message.chat_id)
        else:
            update.message.reply_text('Your game has not started yet. You will get your target once the game starts')
    else:
        update.message.reply_text('You are not enrolled in a game')


def send_target(context, chat_id):
    """ Send the target of the assassin with the specified id to that person

    This includes gathering the details from the database and formatting the
    information with a little window-dressing with random skills
    """
    # Gather needed information about target from the database
    target_id, name, code_name, address, major, game_id = get_target_of(chat_id)
    random_skills = ['lockpicking', 'hand-to-hand combat', 'target acquisition',
                     'covert operations', 'intelligence gathering', 'marksmanship',
                     'knife-throwing', 'explosives', 'poison', 'seduction',
                     'disguises', 'exotic weaponry', 'vehicles', 'boobytraps']
    # Compose dossier message with target details and randomly generated skills
    context.bot.send_photo(chat_id,
                           photo=open(os.path.join('images', str(game_id), str(target_id)) + '.jpg', 'rb'),
                           caption='Name: {}\n\nCode name: {}\n\nAddress: {}\n\nMajor: {}\n\nSkills: {}'.format(
                               name,
                               code_name,
                               address,
                               major,
                               (', '.join(random.sample(random_skills, 2)))
                           ))


def leaderboard(update, context):
    """ TODO: Send the leaderboard to the game master issuing the command

    The leaderboard is sorted first by alive/dead and second by number of kills
    and should include things like name, codename and tally.
    Example format:
    ✅ | John Doe      | MrDoe  | 2
    ✅ | Some Pacifist | Hippie | 0
    ❌ | Jane Doe      | MrsDoe | 1
    ❌ | Doc Brown     | TheDoc | 0
    """
    pass


def game_overview(update, context):
    """ TODO Send a complete and comprehensive list of the players enrolled in the game,
     giving the game master a good overview of players alive and the paths the game has
    taken so far (perhaps send a graphical overview) """
    pass


def confirm_kill(update, context):
    """ TODO Player claims to have killed their target, send confirmation request to target, which can be contested

    This includes setting the presumed_dead value of the target to one
    and sending out a message along these lines "Your hunter claims to have killed you!
    Enter /confirmdead if this is true, if not contact your game master"
    The /confirmdead command will lead the user to the confirm_dead function
    """
    pass


def confirm_dead(update, context):
    """ TODO Player confirms they have been killed, check if they are actually presumed dead and if so
    kill them off by setting their target value to NULL and sending their previous target to their killer
    """
    pass


def task(update, context):
    pass


def task_answer(update, context):
    pass


def pm(update, context):
    """ Admin command that lets developers send personal messages to people by specifying their telegram_id"""
    if update.message.chat_id in get_developers():
        # Context args are chat id of the user to PM followed by message to be sent
        message = ' '.join(context.args[1:])
        logger.info('PMed {x}: {y}'.format(x=context.args[0], y=message))
        context.bot.send_message(context.args[0], message)
    else:
        update.message.reply_text('Forbidden')


def rules(update, context):
    update.message.reply_text('These are the rules for your game:\n' + get_rules())


def get_rules():
    rule_text = (''
                 '1. Your task is to assassinate your assigned target by shooting them with a water gun. (Kills must '
                 'be reported to gamemaster bot by both assassin and target)\n '
                 '2. Targets are always safe in their room, in classes, and places of work.\n'
                 '3. When you assassinate your target, their target becomes your new target.\n'
                 '4. If you are shot by your target, you are then disabled for 24 hrs.\n'
                 '5. The last person alive or the person with the most assassinations at the end of the game is the  '
                 'winner\n '
                 '6. Always stay 1.5 meters away from other assassins. They\'re assassins after all\n'
                 '7. If per official guidelines you are required to quarantine, or you have corona-like symptoms, '
                 'you\'ll have to withdraw from the game\n '
                 '8. You mustn\'t leave the premises for more than 3 whole days\n')
    return rule_text


def help_overview(update, context):
    logger.info('User name: {x}, id: {y} requested help.'.format(x=update.message.from_user.first_name,
                                                                 y=update.message.chat_id))
    update.message.reply_text(
        'This Bot was written by github.com/ossner. The code is licensed under the MIT license\n\n'
        '*User commands:*\n'
        '/help - Get an overview of the available commands\n'
        '/rules - Get an overview of the rules for the game (subject to change)\n'
        '/joingame - Join an upcoming game\n'
        '/dropout - Drop out of the game you\'re registered to\n'
        '/newgame - Create a new game of Assassins where you\'re the admin\n'
        '/confirmkill - Confirm target elimination\n'
        '/dossier - Re-send your target\'s information\n'
        '/task - Submit an answer for the current task\n\n'
        '*Admin commands:*\n'
        '/leaderboard - Get the scoreboard of the game you\'re hosting\n'
        '/freeforall - Set your game to free-for-all mode, where everyone can be shot by anyone. '
        'Send /freeforall again to cancel\n'
        '/broadcast - Send a message to all participating players currently alive\n'
        '/broadcastall - Send a message to all participating players, dead or alive\n'
        '/burn - Burn an assassin after non-compliance to the rules (or when you feel like it)',
        parse_mode=ParseMode.MARKDOWN)


def dirty(string):
    return re.compile(r'[@!#$%^&*<>?|}{~;]').search(string)


def free_for_all(update, context):
    pass


def main():
    updater = Updater(os.getenv("SAS_TOKEN"), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start, run_async=True))

    dp.add_handler(CommandHandler('newgame', new_game, run_async=True))

    dp.add_handler(CommandHandler('startgame', start_game, run_async=True))

    dp.add_handler(CommandHandler('stopgame', stop_game, run_async=True))

    dp.add_handler(CommandHandler('broadcast', broadcast, run_async=True))

    dp.add_handler(MessageHandler(Filters.photo & Filters.caption(r'/broadcast'), broadcast, run_async=True))

    dp.add_handler(CommandHandler('broadcastall', broadcast_all, run_async=True))

    dp.add_handler(MessageHandler(Filters.photo & Filters.caption(r'^(/broadcastAll)|(/broadcastall)'), broadcast_all,
                                  run_async=True))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('joinGame', join_game, run_async=True)],
        states={
            # After getting key, you move into method in the value
            GAMECODE: [MessageHandler(Filters.text & ~Filters.command, get_assassin_name, run_async=True)],
            ASSASSINNAME: [MessageHandler(Filters.text & ~Filters.command, get_code_name, run_async=True)],
            CODENAME: [MessageHandler(Filters.text & ~Filters.command, check_needs_weapon, run_async=True)],
            WEAPON: [CallbackQueryHandler(get_address, pattern=r'^\d$', run_async=True)],
            ADDRESS: [MessageHandler(Filters.text & ~Filters.command, get_major, run_async=True)],
            MAJOR: [MessageHandler(Filters.text & ~Filters.command, get_image, run_async=True)],
            PICTURE: [MessageHandler(Filters.all & ~Filters.command, signup_done, run_async=True)]
        },
        fallbacks=[
            MessageHandler(Filters.command, cancel, run_async=True),
        ]))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('task', task, run_async=True)],
        states={
            # After getting key, you move into method in the value
            # TODO Make this conversation accessible to game masters in order to
            #  create a task and to users in order to answer a task
            MESSAGE: [MessageHandler(Filters.text & ~Filters.command, task_answer, run_async=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)]))

    dp.add_handler(CommandHandler('dropout', dropout, run_async=True))

    dp.add_handler(CommandHandler('burn', burn, run_async=True))

    dp.add_handler(CommandHandler('freeforall', free_for_all, run_async=True))

    dp.add_handler(CommandHandler('dossier', dossier, run_async=True))

    dp.add_handler(CommandHandler('leaderboard', leaderboard, run_async=True))

    dp.add_handler(CommandHandler('players', game_overview, run_async=True))

    dp.add_handler(CommandHandler('confirmKill', confirm_kill, run_async=True))

    dp.add_handler(CommandHandler('confirmDead', confirm_dead, run_async=True))

    dp.add_handler(CommandHandler('rules', rules, run_async=True))

    dp.add_handler(CommandHandler('help', help_overview, run_async=True))

    dp.add_handler(CommandHandler('pm', pm, run_async=True))

    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
