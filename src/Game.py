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
        self.id = random.randint(100000, 999999) # creates a game id that might not be unique. it would be easy enough to check if it's taken,
                                                 # but I like a little danger in my life
        self.enterData()


    def enterData(self):
        cursor.execute("INSERT INTO Games (id, master) VALUES (%s, %s);",(self.id, self.master))
        connection.commit()


# checks whether or not the user with the id already registered a game in progress
def checkPresent(master):
    cursor.execute("SELECT master FROM Games where master=%s AND stopped=0 LIMIT 1", (master, ))
    connection.commit()
    return cursor.fetchone()


# checks if the user with this id already has 10 past games in the database, if so return false
def underGameLimit(master):
    cursor.execute("SELECT id FROM Games where master=%s", (master, ))
    connection.commit()
    return len(cursor.fetchall()) < 10



def checkStarted(master):
    cursor.execute("SELECT master FROM Games where master=%s AND started=1 LIMIT 1", (master, ))
    connection.commit()
    return cursor.fetchone()

# Checks if there is a game by this gamemaster which is not stopped
def checkStartable(master):
    cursor.execute("SELECT master FROM Games where master=%s AND stopped=0 LIMIT 1", (master, ))
    connection.commit()
    return cursor.fetchone()


def startGame(master):
    cursor.execute("UPDATE Games SET started=1 WHERE master=%s AND stopped=0;", (master, ))
    connection.commit()
    # TODO: distribute targets, send out dossiers
    # TODO: check if min player number has been reached of if game has already started, return false

def stopGame(master):
    cursor.execute("UPDATE Games SET started=0, stopped=1 WHERE master=%s;", (master, ))
    connection.commit()
    # TODO: send out leaderboard and notify players

# Send out leaderboard of game
def leaderboard(master, redacted):
    # Send game info like this: "Place  |   Codename   |   real name (if redacted false)    |   Kill tally"
    pass

# retrieves all players currently enrolled in this masters running game
def getPlayerlist(master):
    cursor.execute("SELECT assassins.id from assassins INNER JOIN games on games.id=assassins.game AND games.master=%s AND games.started=1", (master, ))
    connection.commit()
    return cursor.fetchall()


def checkJoinable(id):
    cursor.execute("SELECT * from games WHERE id=%s AND started=0 AND stopped=0", (id, ))
    connection.commit()
    return cursor.fetchone()

def playerEnrolled(player_id, master_id):
    cursor.execute("SELECT assassins.code_name FROM assassins INNER JOIN games g ON assassins.game = g.id AND g.master=%s AND assassins.id=%s AND g.started=1", (master_id, player_id))
    connection.commit()
    return cursor.fetchone()
