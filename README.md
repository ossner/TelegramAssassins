# TelegramAssassins

Telegram Bot that manages instances of the live-action game "[Assassins](https://en.wikipedia.org/wiki/Assassin_(game))"

## Setup Guide for Developers

### Get your development bot token

- Create a bot with telegram by sending /newbot to @Botfather and going through the converasation, the names of the bots
  don't matter

- Once Botfather gives you your bot token, create an environment variable called "SAS_TOKEN" and set it to your bot
  token

### Create the Django Project

- Clone this repository and create a Django project in its base directory
  (It's really easy when using PyCharm, but you can also use the command line)

### Set up your Development Environment

- run `python manage.py migrate` in the base directory of the project, this will create your local database called "
  db.sqlite3"

- Set up the database in the base folder as specified in the sqlite-schema script. This will also fill the database with
  dummy values, note that sending messages to these accounts will not work.

You should now be able to run telegrambot.py