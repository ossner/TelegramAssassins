# TelegramAssassins
Telegram Bot that manages instances of the game [Assassins](https://en.wikipedia.org/wiki/Assassin_(game))

## Getting started
This is how you can make your own version of the bot, how you can develop it further or test it

### Prerequisites
- You will need your own Telegram bot, find out more about telegram bots [here](https://core.telegram.org/bots). Once you have your bot, add an environment variable called "SAS_TOKEN" with your Bot's token
- [The python wrapper for telegram bots](https://github.com/python-telegram-bot/python-telegram-bot)
- [MySQL python connector](https://pypi.org/project/mysql-connector-python/)
- A version of pdflatex added to your PATH
- And a [MySQL server](https://dev.mysql.com/downloads/mysql/)

## How it works
Users can send commands to the Bot, these commands will get interpreted and data will be entered into the database

Example:

``/newgame`` is a command that creates a new game where the user who texted the command will be the game master. So the bot carries out this SQL query: ``INSERT INTO games (id, master, username) VALUES (%s, %s, %s);`` where the gameid and the id of the gamemaster will be stored.
