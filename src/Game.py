import random
import os
import mysql.connector

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("MYSQL_ROOT"),
    database='Assassins_Society'
)
cursor = connection.cursor(buffered=True)

class Game:
    def __init__(self, master):
        self.master = master
        self.id = random.randint(100000, 999999) # creates a random 6 digit game id that might not be unique. it would be easy enough to check if it's taken,
                                                 # but I like a little danger in my life
        self.enterData()


    def enterData(self):
        cursor.execute("INSERT INTO games (id, master) VALUES (%s, %s);", (self.id, self.master))
        connection.commit()


# checks whether or not the user with the id already registered a game
def checkPresent(master, started=False):
    if started:
        cursor.execute("SELECT master FROM games WHERE master=%s AND started=1;", (master, ))
    else:
        cursor.execute("SELECT master FROM games where master=%s;", (master, ))
        connection.commit()
    return cursor.fetchone()

def checkStartable(master):
    cursor.execute("SELECT master FROM games where master=%s AND started=0;", (master, ))
    connection.commit()
    return cursor.fetchone()

def startGame(master):
    cursor.execute("UPDATE games SET started=1 WHERE master=%s;", (master, ))
    connection.commit()
    return assignTargets(master)

def assignTargets(master):
    playerIds = getPlayerlist(master)
    for i in range(len(playerIds)):
        cursor.execute("UPDATE assassins SET target=%s WHERE id=%s;", ((playerIds[(i+1)%len(playerIds)][0]), playerIds[i][0]))
    connection.commit()
    return playerIds

def stopGame(master):
    # TODO: send out leaderboard and notify players
    # deleting the game will cascade and delete all assassins registered to that game
    cursor.execute("DELETE FROM games WHERE master=%s;", (master, ))
    connection.commit()

# Send out leaderboard of game
def leaderboard(master, redacted):
    # Send game info like this: "Place  |   Codename   |   real name (if redacted false)    |   Kill tally"
    pass

# retrieves all players currently enrolled in this masters running game
def getPlayerlist(master):
    cursor.execute("SELECT assassins.id from assassins INNER JOIN games on games.id=assassins.game AND games.master=%s AND games.started=1;", (master, ))
    connection.commit()
    return cursor.fetchall()

def getMaster(game_id):
    cursor.execute("SELECT games.master FROM games WHERE id=%s", (game_id, ))
    connection.commit()
    return cursor.fetchone()


def checkJoinable(id):
    cursor.execute("SELECT * from games WHERE id=%s AND started=0;", (id, ))
    connection.commit()
    return cursor.fetchone()

def playerEnrolled(player_id, master_id):
    cursor.execute("SELECT assassins.code_name FROM assassins INNER JOIN games g ON assassins.game = g.id AND g.master=%s AND assassins.id=%s AND g.started=1;", (master_id, player_id))
    connection.commit()
    return cursor.fetchone()
