import mysql.connector
import os

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("MYSQL_ROOT"),
    database='Assassins_Society'
)
cursor = connection.cursor(buffered=True)

class Assassin:
    def __init__(self, name, codename, address, chat_id, major, weapon, idgame):
        self.name = name
        self.codename = codename
        self.address = address
        self.chat_id = chat_id
        self.major = major
        self.weapon = weapon
        self.idgame = idgame
        self.enterData()

    def enterData(self):
        cursor.execute("INSERT INTO ASSASSINS (`id`, `first_name`, `code_name`, `address`, `major`, `needs_weapon`, `game`)"
        "VALUES (%s, %s, %s, %s, %s, %s, %s)", (self.chat_id, self.name, self.codename, self.address, self.major, self.weapon, self.idgame))
        connection.commit()

# Returns a result if the player with the given id has joined a game that is either upcoming or already started
def checkJoined(assassin_id, started=False):
    if started:
        cursor.execute("SELECT * from assassins INNER JOIN games on games.id=assassins.game AND games.started=1 AND assassins.id=%s", (assassin_id,))
    else:
        cursor.execute("SELECT * from assassins INNER JOIN games on games.id=assassins.game AND assassins.id=%s", (assassin_id,))
    connection.commit()
    return cursor.fetchone()

def getPlayerCodeName(assassin_id, master_id):
    cursor.execute("SELECT assassins.code_name FROM assassins INNER JOIN games g ON assassins.game = g.id"
    "AND g.master=%s AND assassins.id=%s AND g.started=1", (master_id, assassin_id))
    connection.commit()
    return cursor.fetchone()

# Removes a player from the game. Either dropout, burning or elimination. If dropout or burning, the kill tally will not get incremented
# If the game was running, update the tagret list, as the hunter of the eliminated player will get the target of them as the new target
# Also return the id of the hunter if possible, so that the hunter will get the new information of their target
# If the player was not enrolled in a running game, simply remove them from the table
def eliminatePlayer(assassin_id, kill=False):
    if checkJoined(assassin_id, True):
        hunter = getHunter(assassin_id)
        # Increments hunter kill tally
        if kill:
            cursor.execute("UPDATE assassins a2 INNER JOIN assassins a1 ON a1.target=a2.id SET a1.target=a2.target, a2.target=NULL, a2.dead=1, a1.tally=a1.tally+1 WHERE a2.id=%s;", (assassin_id, ))
        # Does not increment hunter kill tally
        else:
            cursor.execute("UPDATE assassins a2 INNER JOIN assassins a1 ON a1.target=a2.id SET a1.target=a2.target, a2.target=NULL, a2.dead=1 WHERE a2.id=%s;", (assassin_id, ))
    # Player was not enrolled in a running game, simply remove them from the database
    else:
        cursor.execute("DELETE from assassins where id=%s", (assassin_id, ))
        connection.commit()
        return None
    connection.commit()
    return hunter

def getHunter(assassin_id):
    cursor.execute("SELECT id FROM assassins where target=%s", (assassin_id, ))
    connection.commit()
    return cursor.fetchone()

def checkAlive(assassin_id):
    cursor.execute("SELECT id FROM assassins WHERE id=%s AND dead=0", (assassin_id, ))
    connection.commit()
    return cursor.fetchone()

# returns players targets id, game, and necessary assassin info
def getTargetInfo(assassin_id):
    cursor.execute("SELECT t.id, t.game, t.first_name, t.code_name, t.address, t.major FROM assassins h INNER JOIN assassins t ON h.target=t.id WHERE h.id=%s;", (assassin_id, ))
    connection.commit()
    return cursor.fetchone()