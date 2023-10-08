import json

from interactions import (
    Attachment,
    Client,
    Intents,
    OptionType,
    SlashContext,
    listen,
    slash_command,
    slash_option,
)
from interactions.api.voice.audio import AudioVolume

bot: Client = Client(intents=Intents.ALL)
sound_wrapper: dict = {}
command_queue: list = []
connected = False


@listen()
async def on_ready():
    with open("sounds.json", "r") as file:
        global sound_wrapper
        sound_wrapper = json.load(file)
    print(f"{bot.user} está no ar!")


@listen()
async def on_message_create(ctx):
    if ctx.message.author == bot.user:
        return

    sound_url = sound_wrapper.get(ctx.message.content.lower())
    global connected
    

    if sound_url:
        if ctx.message.author.voice:
            if connected:
                command_queue.append(sound_url)
                await ctx.message.channel.send("Seu som foi adicionado à fila.")
            else:
                voice_state = await ctx.message.author.voice.channel.connect()
                connected = True
                await voice_state.play(AudioVolume(sound_url))
                if command_queue:
                    for command in command_queue:
                        await voice_state.play(AudioVolume(command))
                    command_queue.clear()
                await voice_state.disconnect()
                connected = False
        else:
            await ctx.message.channel.send(
                "Você precisa estar em um canal de voz para reproduzir sons."
            )


@slash_command(name="add_sound", description="Adiciona um som ao bot.")
@slash_option(
    name="key",
    description="Palavra chave para o som.",
    opt_type=OptionType.STRING,
    required=True,
)
@slash_option(
    name="sound",
    description="Arquivo de som",
    opt_type=OptionType.ATTACHMENT,
    required=True,
)
async def add_sound(ctx: SlashContext, key: str, sound: Attachment):
    if sound_wrapper.get(key.lower()):
        await ctx.send("Esse som já existe.")
        return
    else:
        sound_wrapper[key.lower()] = sound.url
        with open("sounds.json", "w") as file:
            json.dump(sound_wrapper, file)
        await ctx.send("Som adicionado com sucesso.")


if __name__ == "__main__":
    with open("config.json", "r") as config:
        bot.start(json.load(config)["token"])
