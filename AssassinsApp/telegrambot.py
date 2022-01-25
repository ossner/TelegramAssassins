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

from AssassinsApp.bot_database_interface import get_developers, add_game, db_start_game, game_started, \
    get_assassin, get_master, add_assassin, game_exists, kill_player, remove_player, get_target_of, get_assassin_ids, \
    assign_targets, get_game_id, set_presumed_dead, get_hunter, last_man_standing, change_subscription, get_subscribers, \
    get_active_task, set_task_inactive, get_three_joker_users, add_task, give_task_point, set_game_stopped

BASE_DIR = Path(__file__).resolve().parent.parent

GAMECODE, ASSASSINNAME, CODENAME, WEAPON, ADDRESS, MAJOR, PICTURE = range(7)  # Constants needed for conversation

MESSAGE, REGEX, ANSWER = 0, 1, 2  # Constant for the task conversation, since there is only one step

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
    update.message.reply_text('Cancelled the conversation. Roger.')
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
    game_id = get_game_id(game_master_id=update.message.chat_id)
    if game_id:
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
    if get_game_id(game_master_id=update.message.chat_id):
        if game_started(get_game_id(game_master_id=update.message.chat_id)):
            logger.info('User name: {x}, id: {y} stopped their game.'.format(x=update.message.from_user.first_name,
                                                                             y=update.message.chat_id))
            for id in get_assassin_ids(get_game_id(game_master_id=update.message.chat_id)):
                try:
                    context.bot.send_message(id, 'That\'s it! This round of Secret Assassins Society has come to a close. '
                                                 'Take a look at the final leaderboard:')
                    context.bot.send_message(id, get_leaderboard(get_game_id(game_master_id=update.message.chat_id)),
                                         parse_mode=ParseMode.MARKDOWN_V2)
                except Unauthorized:
                    logger.warning('User {} could not be contacted'.format(id))
            set_game_stopped(get_game_id(game_master_id=update.message.chat_id))
            update.message.reply_text('Game has been stopped!')
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
    if get_game_id(game_master_id=update.message.chat_id):
        try:
            photo_file = update.message.photo[-1].file_id
            photo_caption = update.message.caption.strip('/broadcastAll ').strip('/broadcastall ')
            logger.info('User name: {x}, id: {y} broadcast an image.'.format(x=update.message.from_user.first_name,
                                                                             y=update.message.chat_id))
            players = get_assassin_ids(get_game_id(update.message.chat_id), only_alive=only_alive)
            for player in players:
                try:
                    context.bot.send_photo(player, photo_file, caption=photo_caption)
                except Unauthorized:
                    logger.warning('User {} could not be contacted'.format(player))
            update.message.reply_text('Your image has been forwarded to {} players'.format(len(players)))
        except IndexError:
            if context.args:
                message = ' '.join(context.args)
                logger.info('User name: {x}, id: {y} broadcast {z}.'.format(x=update.message.from_user.first_name,
                                                                            y=update.message.chat_id,
                                                                            z=message))
                players = get_assassin_ids(get_game_id(update.message.chat_id), only_alive=only_alive)
                for player in players:
                    try:
                        context.bot.send_message(player, message)
                    except Unauthorized:
                        logger.warning('User {} could not be contacted'.format(player))
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
    if get_assassin(update.message.chat_id):
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
    else:
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
                    get_master(context.user_data['game_id'])['master_user']))
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
    user = get_assassin(update.message.chat_id)
    if user:
        logger.info('User name: {x}, id: {y} dropped out of a game.'.format(x=update.message.from_user.first_name,
                                                                            y=update.message.chat_id))
        if game_started(get_game_id(participant_id=update.message.chat_id)):
            kill_player(update.message.chat_id)  # The game has started, so kill the player without attributing points
            hunter_id = get_hunter(user['target'])['id']
            context.bot.send_message(hunter_id, "Your target dropped out of the game. This is your new target:")
            send_target(context, hunter_id)
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
    if get_game_id(game_master_id=update.message.chat_id):
        #  Check command args validity
        if context.args and re.match(r"^\d+$", context.args[0]):
            player_id = context.args[0]
            assassin = get_assassin(player_id)
            logger.info('User name: {x}, id: {y} burned {z}.'.format(x=update.message.from_user.first_name,
                                                                     y=update.message.chat_id,
                                                                     z=player_id))
            #  Check if player is actually enrolled in this persons game TODO remove and handle with db
            if get_game_id(game_master_id=update.message.chat_id) == get_game_id(participant_id=player_id):
                kill_player(player_id)
                send_target(context, get_hunter(assassin['target'])['id'])
            else:
                update.message.reply_text('This assassins is not enrolled in your game')
        else:
            update.message.reply_text('Specified player id is invalid')
    else:
        update.message.reply_text('You do not have a game registered')


def dossier(update, context):
    """ User requested their target's dossier, send all the needed information """
    player = get_assassin(update.message.chat_id)
    if player and player['target'] is not None:
        if game_started(get_game_id(participant_id=update.message.chat_id)):
            logger.info('User name: {x}, id: {y} requested their dossier.'.format(x=update.message.from_user.first_name,
                                                                                  y=update.message.chat_id))
            send_target(context, update.message.chat_id)
        else:
            update.message.reply_text('Your game has not started yet. You will get your target once the game starts')
    else:
        update.message.reply_text('You are either dead, or not enrolled in a game')


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
    try:
        context.bot.send_photo(chat_id,
                               photo=open(os.path.join('images', str(game_id), str(target_id)) + '.jpg', 'rb'),
                               caption='Name: {}\n\nCode name: {}\n\nAddress: {}\n\nMajor: {}\n\nSkills: {}'.format(
                                   name,
                                   code_name,
                                   address,
                                   major,
                                   (', '.join(random.sample(random_skills, 2)))
                               ))
    except Unauthorized:
        logger.error("Sending message to {} caused an exception".format(chat_id))


def get_leaderboard(game_id):
    all_assassin_ids = get_assassin_ids(game_id)
    all_assassin_dicts = []
    for id in all_assassin_ids:
        all_assassin_dicts.append(get_assassin(id))
    new_dicts = sorted(all_assassin_dicts, key=lambda k: k['tally'], reverse=True)
    new_dicts_c = new_dicts.copy()
    for dict in new_dicts:
        if dict['target'] is None:
            new_dicts_c.remove(dict)
            new_dicts_c.append(dict)
    ret_str = "`alive | codename               | kills`\n`----------------------------------------`"
    for dict in new_dicts_c:
        ret_str += "\n`{:<7}| {:<23}| {}`".format("✅" if dict['target'] else "❌", dict['code_name'], dict['tally'])
    return ret_str


def leaderboard(update, context):
    """ Send the leaderboard to the person issuing the command

    The leaderboard is sorted first by alive/dead and second by number of kills
    and should include things like name, codename and tally.
    Example format:
    ✅ | John Doe      | MrDoe  | 2
    ✅ | Some Pacifist | Hippie | 0
    ❌ | Jane Doe      | MrsDoe | 1
    ❌ | Doc Brown     | TheDoc | 0
    """
    # Assign a value to game_id if this assassin is either a participant or a master, else None
    game_id = get_game_id(game_master_id=update.message.chat_id) if get_game_id(game_master_id=update.message.chat_id) \
        else get_game_id(participant_id=update.message.chat_id)
    if game_id:
        logger.info('User name: {x}, id: {y} requested the leaderboard.'.format(x=update.message.from_user.first_name,
                                                                                y=update.message.chat_id))
        ret_str = get_leaderboard(game_id)
        update.message.reply_text(ret_str, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        update.message.reply_text('You are neither enrolled in a game, nor do you have one registered to yourself')


def game_overview(update, context):
    """ TODO Send a complete and comprehensive list of the players enrolled in the game,
     giving the game master a good overview of players alive and the paths the game has
    taken so far (perhaps send a graphical overview) """
    if get_game_id(game_master_id=update.message.chat_id):
        pass


def confirm_kill(update, context):
    """ Player claims to have killed their target, send confirmation request to target, which can be contested

    This includes setting the presumed_dead value of the target to one
    and sending out a message along these lines "Your hunter claims to have killed you!
    Enter /confirmdead if this is true, if not contact your game master"
    The /confirmdead command will lead the user to the confirm_dead function
    """
    hunter = get_assassin(update.message.chat_id)
    #  Check if this person is enrolled in a game and has a target assigned
    if hunter and hunter['target']:
        master_username = get_master(hunter['game'])['master_user']
        #  Check if the hit was already reported
        if get_assassin(hunter['target'])['presumed_dead'] == 0:
            logger.info('User name: {x}, id: {y} claimed a kill.'.format(x=update.message.from_user.first_name,
                                                                         y=update.message.chat_id))
            update.message.reply_text(
                'Alright, I will check with your target. If you don\'t hear back from me soon, text your game master '
                '@{}'.format(master_username))
            #  Set the target's presumed dead to 1 so the target can confirm that they are dead
            set_presumed_dead(hunter['target'])
            context.bot.send_message(hunter['target'], 'Your hunter has claimed your assassination. If this is true, '
                                                       'issue the command /confirmDead otherwise text your game '
                                                       'master @{}'.format(master_username))
        else:
            logger.warning('User name: {x}, id: {y} claimed a kill for the second time.'.format(
                x=update.message.from_user.first_name,
                y=update.message.chat_id))
            update.message.reply_text(
                'You already issued this command, talk to your game master @{}'.format(master_username))
    else:
        update.message.reply_text('You are not enrolled in a game or don\'t have a target assigned to you')


def confirm_dead(update, context):
    """ Player confirms they have been killed, check if they are actually presumed dead and if so
    kill them off by setting their target value to NULL and sending their previous target to their killer
    """
    target = get_assassin(update.message.chat_id)
    if target:
        if target['presumed_dead'] == 1:
            logger.info('User name: {x}, id: {y} confirmed they are dead.'.format(x=update.message.from_user.first_name,
                                                                                  y=update.message.chat_id))
            update.message.reply_text('You were too weak for the society')
            killer = get_hunter(target['id'])
            kill_player(target['id'], killer_id=killer['id'])
            for subscriber in get_subscribers(target['game']):
                context.bot.send_message(subscriber,
                                         "There has been an assassination! {} wiped out {} bringing their tally up to "
                                         "{}".format(
                                             killer['code_name'], target['code_name'], (killer['tally'] + 1)))
            context.bot.send_message(get_master(target['game'])['master_id'],
                                     "There has been an assassination! {} wiped out {} bringing their tally up to "
                                     "{}".format(
                                         killer['code_name'], target['code_name'], (killer['tally'] + 1)))
            if last_man_standing(target['game']):
                for id in get_assassin_ids(target['game']):
                    context.bot.send_message(id, 'That\'s it! This round of the Secret Assassins Society has come to a '
                                                 'close and {} has won by being the last (wo)man standing with {} eliminations. '
                                                 'Take a look at the final leaderboard:'
                                             .format(killer['code_name'], killer['tally']))
                    context.bot.send_message(id, get_leaderboard(get_game_id(game_master_id=update.message.chat_id)),
                                             parse_mode=ParseMode.MARKDOWN_V2)
                    set_game_stopped(target['game'])
                pass
            else:
                send_target(context, killer['id'])
        else:
            update.message.reply_text('Nobody has claimed your kill (yet)')
            pass
    else:
        update.message.reply_text('You are not enrolled in a game')


def subscribe(update, context):
    user = get_assassin(update.message.chat_id)
    logger.info('User name: {x}, id: {y} toggled their subscription.'.format(x=update.message.from_user.first_name,
                                                                             y=update.message.chat_id))
    if user:  # User exists
        if user['subscribed'] == 0:  # User is not yet subscribed
            update.message.reply_text('You will be notified of all assassinations on your game')
        else:  # User is a subscriber and wants to unsubscribe
            update.message.reply_text('Alright, you will no longer receive updates on kills in your game')
        change_subscription(update.message.chat_id)
    else:
        update.message.reply_text('You are not enrolled in a game')


def task(update, context):
    # Check if user is game master or if user is assassin
    if get_game_id(game_master_id=update.message.chat_id):
        game_id = get_game_id(game_master_id=update.message.chat_id)
        if get_active_task(game_id):
            logger.info(
                'User: {x}, id: {y} stopped their active task.'.format(x=update.message.from_user.first_name,
                                                                       y=update.message.chat_id))
            set_task_inactive(game_id)
            users_to_burn = get_three_joker_users(game_id)
            print('Users to burn: {}'.format(users_to_burn))
            for t_id in users_to_burn:
                hunter = get_hunter(t_id)
                kill_player(t_id)
                context.bot.send_message(hunter['id'], 'Your target has been burned after not completing a task. This '
                                                       'is your new target:')
                send_target(context, hunter['id'])
            update.message.reply_text('Your current task has been stopped and jokers have been updated. {} users have '
                                      'been burned'.format(len(users_to_burn)))
        else:
            logger.info(
                'User: {x}, id: {y} creates a new task.'.format(x=update.message.from_user.first_name,
                                                                y=update.message.chat_id))
            update.message.reply_text('Specify the task you want your assassins to complete:')
            return MESSAGE
    elif get_game_id(participant_id=update.message.chat_id):
        game_id = get_game_id(participant_id=update.message.chat_id)
        if get_active_task(game_id):
            logger.info(
                'User: {x}, id: {y} tries to answer a task.'.format(x=update.message.from_user.first_name,
                                                                    y=update.message.chat_id))
            update.message.reply_text('Enter the solution to the current task:')
            return ANSWER
        else:
            update.message.reply_text("There is no current task for you to submit")
    else:
        update.message.reply_text("You are not enrolled in a running game")
    return ConversationHandler.END


def task_message(update, context):
    context.user_data['task_message'] = update.message.text
    update.message.reply_text('Got it. Now please enter the solution Regex')
    return REGEX


def task_solution(update, context):
    context.user_data['task_solution'] = update.message.text
    add_task(get_game_id(update.message.chat_id), context.user_data['task_message'], context.user_data['task_solution'])
    for assassin in get_assassin_ids(get_game_id(game_master_id=update.message.chat_id), only_alive=True):
        context.bot.send_message(assassin, 'Your game master has created a task for all assassins:')
        context.bot.send_message(assassin, context.user_data['task_message'])
    update.message.reply_text('Your task has been forwarded to your assassins')
    logger.info(
        'User: {x}, id: {y} created a new task.'.format(x=update.message.from_user.first_name,
                                                        y=update.message.chat_id))
    return ConversationHandler.END


def task_answer(update, context):
    submitted_answer = update.message.text
    pattern = re.compile(get_active_task(get_game_id(participant_id=update.message.chat_id))['solution'])
    if pattern.search(submitted_answer):
        give_task_point(update.message.chat_id)
        update.message.reply_text('You have answered the task correctly!')
        logger.info(
            'User: {x}, id: {y} answered the task correctly.'.format(x=update.message.from_user.first_name,
                                                                     y=update.message.chat_id))
    else:
        update.message.reply_text('This answer is not correct!')
        logger.info(
            'User: {x}, id: {y} answered the task incorrectly with: {z}.'.format(x=update.message.from_user.first_name,
                                                                                 y=update.message.chat_id,
                                                                                 z=submitted_answer))
    return ConversationHandler.END


def pm(update, context):
    """ Admin command that lets developers send personal messages to people by specifying their telegram_id"""
    if update.message.chat_id in get_developers() or update.message.chat_id == 755660906:
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
                 '2. Targets are always safe on their floor, in classes, and places of work.\n'
                 '3. When you assassinate your target, their target becomes your new target.\n'
                 '4. If you are shot by your target, you are then disabled for 24 hrs.\n'
                 '5. The last person alive or the person with the most assassinations at the end of the game is the  '
                 'winner\n '
                 '6. Always stay 1.5 meters away from other assassins. They\'re assassins after all\n'
                 '7. If per official guidelines you are required to quarantine, or you have corona-like symptoms, '
                 'you\'ll have to withdraw from the game\n '
                 '8. You mustn\'t leave the premises for more than 3 whole days\n'
                 '9. Failure to complete an assigned task will result in you getting burned. You have 2 Jokers.'
                 '10. The Game Master is always right.')
    return rule_text


def help_overview(update, context):
    logger.info('User name: {x}, id: {y} requested help.'.format(x=update.message.from_user.first_name,
                                                                 y=update.message.chat_id))
    update.message.reply_text(
        'This Bot was written by github.com/ossner\n\n'
        '*User commands:*\n'
        '/help - Get an overview of the available commands\n'
        '/rules - Get an overview of the rules for the game (subject to change)\n'
        '/joingame - Join an upcoming game\n'
        '/dropout - Drop out of the game you\'re registered to\n'
        '/subscribe - subscribe/unsubscribe to all assassinations in your game\n'
        '/newgame - Create a new game of Assassins where you\'re the admin\n'
        '/confirmkill - Confirm target elimination\n'
        '/dossier - Re-send your target\'s information\n'
        '/task - Submit an answer for the current task\n'
        '/leaderboard - Get the scoreboard of the game you\'re hosting\n\n'
        '*Admin commands:*\n'
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
    updater = Updater(os.getenv("SAS_TOKEN"), use_context=True, request_kwargs={'read_timeout': 20, 'connect_timeout': 30})
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start, run_async=True))

    dp.add_handler(CommandHandler('newgame', new_game, run_async=True))

    dp.add_handler(CommandHandler('startgame', start_game, run_async=True))

    dp.add_handler(CommandHandler('stopgame', stop_game, run_async=True))

    dp.add_handler(CommandHandler('broadcast', broadcast, run_async=True))

    dp.add_handler(MessageHandler(Filters.photo & Filters.caption(r'/broadcast'), broadcast, run_async=True))

    dp.add_handler(CommandHandler('broadcastall', broadcast_all, run_async=True))

    dp.add_handler(
        MessageHandler(Filters.photo & Filters.caption_regex(r'^(/broadcastall)|(/broadcastAll).*'), broadcast_all,
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
            REGEX: [MessageHandler(Filters.text & ~Filters.command, task_solution, run_async=True)],
            MESSAGE: [MessageHandler(Filters.text & ~Filters.command, task_message, run_async=True)],
            ANSWER: [MessageHandler(Filters.text & ~Filters.command, task_answer, run_async=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)]))

    dp.add_handler(CommandHandler('dropout', dropout, run_async=True))

    dp.add_handler(CommandHandler('burn', burn, run_async=True))

    dp.add_handler(CommandHandler('subscribe', subscribe, run_async=True))

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
