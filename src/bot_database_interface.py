import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = os.path.join(BASE_DIR, 'db.sqlite3')


def get_developers():
    """ Gets a list of developer id's (e.g. for checking privileges)
    :return: a list of telegram IDs of registered developers
    """
    con, cur = connect()
    return [i[0] for i in cur.execute("SELECT id FROM Admins").fetchall()]


def add_task(game_id, message, solution):
    con, cur = connect()
    cur.execute("INSERT INTO Task (message, solution, game) VALUES (?, ?, ?);", (message, solution, game_id))
    con.commit()


def get_active_task(game_id):
    con, cur = connect()
    fields = cur.execute("SELECT id, message, solution FROM Task WHERE game=? AND active=1", (game_id,)).fetchone()
    if fields:
        return {
            'id': fields[0],
            'message': fields[1],
            'solution': fields[2]
        }
    else:
        return None


def set_task_inactive(game_id):
    con, cur = connect()
    cur.execute("UPDATE Task SET active=0 WHERE game=? AND active=1", (game_id,))
    cur.execute("UPDATE Assassins SET jokers_used=jokers_used+1 WHERE task_answered=0 AND target IS NOT NULL AND game=?", (game_id,))
    cur.execute("UPDATE Assassins SET task_answered=0 WHERE game=?", (game_id,))
    con.commit()


def get_three_joker_users(game_id):
    con, cur = connect()
    return [i[0] for i in cur.execute("SELECT id FROM Assassins WHERE jokers_used=3 AND target IS NOT NULL AND game=?", (game_id,)).fetchall()]


def give_task_point(user_id):
    con, cur = connect()
    cur.execute("UPDATE Assassins SET task_answered=1 WHERE id=?", (user_id,))
    con.commit()


def add_game(game_id, master_id, master_name):
    """ Tries to add a game with the provided parameters
    :return: True if the insert was successful, False if it couldn't be inserted due to duplicates
    """
    con, cur = connect()
    try:
        cur.execute("INSERT INTO Games(id, game_master_id, game_master_user) VALUES (?, ?, ?)",
                    (game_id, master_id, master_name,))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def db_start_game(game_id):
    con, cur = connect()
    cur.execute("UPDATE Games SET started=1 WHERE id=?", (game_id,))
    con.commit()


def game_exists(game_id):
    con, cur = connect()
    return cur.execute("SELECT * FROM Games WHERE id=?", (game_id,)).fetchone()


def game_started(game_id):
    con, cur = connect()
    return cur.execute("SELECT * FROM Games WHERE id=? AND started=1", (game_id,)).fetchone()


def get_assassin(user_id):
    con, cur = connect()
    field_list = cur.execute("SELECT id, name, code_name, target, presumed_dead, tally, subscribed, game "
                             "FROM Assassins WHERE id=?", (user_id,)).fetchone()
    if field_list:
        return {
            'id': field_list[0],
            'name': field_list[1],
            'code_name': field_list[2],
            'target': field_list[3],
            'presumed_dead': field_list[4],
            'tally': field_list[5],
            'subscribed': field_list[6],
            'game': field_list[7],
        }
    else:
        return None


def last_man_standing(game_id):
    """ Returns None if there are multiple people still in the game (i.e. no target assigned to themselves) """
    con, cur = connect()
    return cur.execute("SELECT id FROM Assassins WHERE target=id AND game = ?", (game_id,)).fetchone()


def set_presumed_dead(user_id):
    con, cur = connect()
    cur.execute("UPDATE Assassins SET presumed_dead=1 WHERE id = ?", (user_id,))
    con.commit()


def get_master(game_id):
    con, cur = connect()
    field_list = cur.execute("SELECT game_master_id, game_master_user FROM Games WHERE id=?", (game_id,)).fetchone()
    if field_list:
        return {
            'master_id': field_list[0],
            'master_user': field_list[1]
        }
    else:
        return None


def get_hunter(user_id):
    """ Return the user who is currently hunting this one"""
    con, cur = connect()
    hunter_id = cur.execute("SELECT id FROM Assassins WHERE target=?", (user_id,)).fetchone()[0]
    return get_assassin(hunter_id)


def add_assassin(chat_id, name, code_name, address, studies, weapon, game_id):
    con, cur = connect()
    try:
        cur.execute("INSERT INTO Assassins(id, name, code_name, address, major, needs_weapon, game)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)", (chat_id, name, code_name, address, studies, weapon, game_id,))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def kill_player(dead_id, killer_id=None):
    con, cur = connect()
    #  Kills off the person specified
    if not game_started(get_game_id(participant_id=dead_id)):
        remove_player(dead_id)
    else:
        # Update target of hunter
        cur.execute("UPDATE Assassins "
                    "SET target=(SELECT target FROM Assassins WHERE id=?) "
                    "WHERE target=?;",
                    (dead_id, dead_id,))
        # Kill off player by setting target to NULL
        cur.execute("UPDATE Assassins "
                    "SET target=NULL, presumed_dead=0 "
                    "WHERE id=?;", (dead_id,))
        if killer_id:  # User has been assassinated and there are points to award
            cur.execute("UPDATE Assassins SET tally=tally+1 where id=?", (killer_id,))
        con.commit()


def remove_player(user_id):
    con, cur = connect()
    cur.execute("DELETE FROM Assassins WHERE id = ?", (user_id,))
    con.commit()


def get_target_of(chat_id):
    con, cur = connect()
    target_id = cur.execute("SELECT target FROM Assassins WHERE id=?", (chat_id,)).fetchone()[0]
    return cur.execute(
        "SELECT id, name, code_name, address, major, game FROM Assassins WHERE id=?", (target_id,)).fetchone()


def get_assassin_ids(game_id, only_alive=False):
    con, cur = connect()
    if only_alive:  # Only return assassins that are alive
        return [i[0] for i in
                cur.execute("SELECT id FROM Assassins WHERE game=? AND target IS NOT NULL", (game_id,)).fetchall()]
    else:
        return [i[0] for i in cur.execute("SELECT id FROM Assassins WHERE game=?", (game_id,)).fetchall()]


def get_game_id(game_master_id=None, participant_id=None):
    con, cur = connect()
    if game_master_id:
        result = cur.execute("SELECT id FROM Games WHERE game_master_id=?", (game_master_id,)).fetchone()
        if result:
            return result[0]
        else:
            return None
    elif participant_id:
        result = cur.execute(
            "SELECT Games.id FROM Games INNER JOIN Assassins ON Games.id=Assassins.game WHERE Assassins.id=?",
            (participant_id,)).fetchone()
        if result:
            return result[0]
        else:
            return None


def get_subscribers(game_id):
    con, cur = connect()
    return [i[0] for i in cur.execute("SELECT id FROM Assassins WHERE game=? AND subscribed=1", (game_id,)).fetchall()]


def assign_targets(game_id):
    con, cur = connect()
    assassins = get_assassin_ids(game_id)
    for i in range(len(assassins)):
        cur.execute("UPDATE Assassins SET target=? WHERE id=?", ((assassins[(i + 1) % len(assassins)]), assassins[i],))
    con.commit()


def change_subscription(user_id):
    con, cur = connect()
    cur.execute("UPDATE Assassins SET subscribed = (subscribed+1)%2 WHERE id=?", (user_id,))
    con.commit()


def set_game_stopped(game_id):
    con, cur = connect()
    cur.execute("UPDATE Games SET started=0 WHERE id=?", (game_id,))
    con.commit()


def connect():
    con = sqlite3.connect(DB_FILE)
    return con, con.cursor()
