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
    def __init__(self, name, codename, address, chat_id, major, idgame):
        self.name = name
        self.codename = codename
        self.address = address
        self.chat_id = chat_id
        self.major = major
        self.idgame = idgame
        self.enterData()

    def enterData(self):
        cursor.execute("INSERT INTO ASSASSINS (`id`, `first_name`, `code_name`, `address`, `major`, `game`) VALUES (%s, %s, %s, %s, %s, %s)", (self.chat_id, self.name, self.codename, self.address, self.major, self.idgame))
        connection.commit()

def checkJoined(assassin_id):
    cursor.execute("SELECT * from assassins INNER JOIN games on games.id=assassins.game AND games.stopped=0 AND assassins.id=%s", (assassin_id,))
    connection.commit()
    return cursor.fetchone()

def getPlayerCodeName(assassin_id, master_id):
    cursor.execute("SELECT assassins.code_name FROM assassins INNER JOIN games g ON assassins.game = g.id AND g.master=%s AND assassins.id=%s AND g.started=1", (master_id, assassin_id))
    connection.commit()
    return cursor.fetchone()

def eliminatePlayer(assassin_id):
    # TODO: If assassin is enrolled in a running game, re-assign target to hunter
    # TODO: If assassin is enrolled in an upcoming game, remove him from table
    cursor.execute("")
    connection.commit()
    return cursor.fetchone()