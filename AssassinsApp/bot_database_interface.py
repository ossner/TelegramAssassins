import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = os.path.join(BASE_DIR, 'db.sqlite3')


def user_has_game(user_id):
    con, cur = connect()
    cur.execute("SELECT * FROM Games WHERE game_master_id=?", (user_id,))
    return not cur.fetchone() is None


def get_developers():
    """ Gets a list of developer id's (e.g. for checking privileges)
    :return: a list of telegram IDs of registered developers
    """
    con, cur = connect()
    return [i[0] for i in cur.execute("SELECT id FROM Admins").fetchall()]


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


def check_joined(user_id):
    con, cur = connect()
    return cur.execute("SELECT * FROM Assassins WHERE id=?", (user_id,)).fetchone()


def get_master(game_id):
    con, cur = connect()
    return cur.execute("SELECT game_master_user FROM Games WHERE id=?", (game_id,)).fetchone()[0]


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
                    "WHERE id=?;", (dead_id, ))
        if killer_id:  # User has been assassinated and there are points to award
            cur.execute("UPDATE Assassins SET tally=tally+1 where id=?", (killer_id,))
        con.commit()


def remove_player(user_id):
    con, cur = connect()
    cur.execute("DELETE FROM Assassins WHERE id = ?", (user_id,))
    con.commit()


def connect():
    con = sqlite3.connect(DB_FILE)
    return con, con.cursor()


def get_target_of(chat_id):
    con, cur = connect()
    return cur.execute(
        "SELECT t.id, t.name,t.code_name,t.address,t.major, t.game FROM Assassins h"
        " INNER JOIN Assassins t ON h.target=t.id WHERE h.id=?", (chat_id,)).fetchone()


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


def assign_targets(game_id):
    con, cur = connect()
    assassins = get_assassin_ids(game_id)
    for i in range(len(assassins)):
        cur.execute("UPDATE Assassins SET target=? WHERE id=?", ((assassins[(i + 1) % len(assassins)]), assassins[i],))
    con.commit()
