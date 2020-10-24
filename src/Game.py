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
    def __init__(self, master, master_username):
        self.master = master
        self.master_username = master_username
        self.id = random.randint(100000, 999999) # creates a random 6 digit game id that might not be unique. it would be easy enough to check if it's taken,
                                                 # but I like a little danger in my life
        self.enterData()


    def enterData(self):
        cursor.execute("INSERT INTO games (id, master, username) VALUES (%s, %s, %s);", (self.id, self.master, self.master_username))
        connection.commit()

# checks whether or not the user with the id already registered a game
def checkPresent(master, started=False):
    if started:
        cursor.execute("SELECT master FROM games WHERE master=%s AND started=1;", (master, ))
    else:
        cursor.execute("SELECT master FROM games WHERE master=%s;", (master, ))
        connection.commit()
    return cursor.fetchone()

def checkStartable(master):
    cursor.execute("SELECT master FROM games WHERE master=%s AND started=0;", (master, ))
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
    saveBackup(getGameid(master)[0])
    cursor.execute("DELETE FROM games WHERE master=%s;", (master, ))
    connection.commit()

def saveBackup(game_id):
    cursor.execute("SELECT * FROM assassins INNER JOIN games ON games.id=assassins.game WHERE games.id=%s;", (game_id, ))
    connection.commit()
    backup = open('images/' + str(game_id) + '/backup.txt', 'w')
    response = cursor.fetchall()
    for line in response:
        backup.write(str(line))
    backup.close()

# retrieves all players currently enrolled in this masters running game
def getPlayerlist(master):
    cursor.execute("SELECT assassins.id, assassins.first_name, assassins.code_name, assassins.tally, assassins.target FROM assassins INNER JOIN games on games.id=assassins.game AND games.master=%s ORDER BY assassins.tally DESC;", (master, ))
    connection.commit()
    return cursor.fetchall()

def getMaster(game_id):
    cursor.execute("SELECT games.master, games.username FROM games WHERE id=%s", (game_id, ))
    connection.commit()
    return cursor.fetchone()

def getGameid(master):
    cursor.execute("SELECT id FROM games WHERE master = %s", (master, ))
    connection.commit()
    return cursor.fetchone()


def checkJoinable(id):
    cursor.execute("SELECT * FROM games WHERE id=%s AND started=0;", (id, ))
    connection.commit()
    return cursor.fetchone()

def playerEnrolled(player_id, master_id):
    cursor.execute("SELECT assassins.code_name FROM assassins INNER JOIN games g ON assassins.game = g.id AND g.master=%s AND assassins.id=%s;", (master_id, player_id))
    connection.commit()
    return cursor.fetchone()
