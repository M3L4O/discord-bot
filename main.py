import json

from interactions import Client, Intents


if __name__ == "__main__":
    bot: Client = Client(intents=Intents.ALL)
    bot.load_extension(name="exts.soundboard")
    with open("config.json", "r") as config:
        bot.start(json.load(config)["token"])
