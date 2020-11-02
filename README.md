# TelegramAssassins
Telegram Bot that manages instances of the game [Assassins](https://en.wikipedia.org/wiki/Assassin_(game))

## How it works
Users can send commands to the Bot, these commands will get interpreted and data will be entered into the database

Example:

``/newgame`` is a command that creates a new game where the user who texted the command will be the game master. So the bot carries out this SQL query: ``INSERT INTO games (id, master, username) VALUES (%s, %s, %s);`` where the gameid and the id of the gamemaster will be stored.
