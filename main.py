import json
import re

from interactions import (
    ActionRow,
    Attachment,
    Button,
    ButtonStyle,
    Client,
    ComponentContext,
    Intents,
    Message,
    OptionType,
    SlashContext,
    component_callback,
    listen,
    slash_command,
    slash_option,
)
from interactions.api.events import (
    Component,
    MessageCreate,
    VoiceUserJoin,
    VoiceUserLeave,
)
from interactions.api.voice.audio import AudioVolume

bot: Client = Client(intents=Intents.ALL)
sound_wrapper: dict = {}
command_queue: list = []
connected = False
pattern = re.compile(r"button_*")


@listen()
async def on_ready():
    with open("sounds.json", "r") as file:
        global sound_wrapper
        sound_wrapper = json.load(file)
    print(f"{bot.user} está no ar!")


@listen()
async def on_message_create(event: MessageCreate):
    if event.message.author == bot.user:
        return
    sound_url = sound_wrapper.get(event.message.content.lower())

    await play_sound(event, sound_url)


@listen()
async def on_voice_user_join(event: VoiceUserJoin):
    if event.author == bot.user:
        global connected
        connected = True


@listen()
async def on_voice_user_leave(event: VoiceUserLeave):
    if event.author == bot.user:
        global connected
        connected = False


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
        layout: list[ActionRow] = [
            ActionRow(
                Button(label="Sim", style=ButtonStyle.SUCCESS, custom_id="yes"),
                Button(label="Não", style=ButtonStyle.DANGER, custom_id="no"),
            )
        ]
        message: Message = await ctx.send(
            "Esse som já existe. Deseja sobreescrever?", components=layout
        )
        response: Component = await bot.wait_for_component(
            messages=message, components=layout
        )
        if response.ctx.custom_id == "no":
            await message.edit(content="Operação cancelada.", components=[])
            return
        else:
            await message.edit(content="Sobreescrevendo...", components=[])
            ctx = response.ctx

    sound_wrapper[key.lower()] = sound.url
    with open("sounds.json", "w") as file:
        json.dump(sound_wrapper, file)
    await ctx.send("Som adicionado com sucesso.")


@slash_command(name="list_sounds", description="Lista todos os sons disponíveis.")
async def list_sounds(ctx: SlashContext):
    sounds = "\n".join(sound_wrapper.keys())
    await ctx.send(f"Os sons disponíveis são:\n{sounds}")


@slash_command(name="remove_sound", description="Remove um som do bot.")
@slash_option(
    name="key",
    description="Palavra chave para o som.",
    opt_type=OptionType.STRING,
    required=True,
)
async def remove_sound(ctx: SlashContext, key: str):
    if sound_wrapper.get(key.lower()):
        layout: list[ActionRow] = [
            ActionRow(
                Button(label="Sim", style=ButtonStyle.SUCCESS, custom_id="yes"),
                Button(label="Não", style=ButtonStyle.DANGER, custom_id="no"),
            )
        ]
        message: Message = await ctx.send(
            "Tem certeza que deseja remover esse som?", components=layout
        )
        response: Component = await bot.wait_for_component(
            messages=message, components=layout
        )
        if response.ctx.custom_id == "no":
            await message.edit(content="Operação cancelada.", components=[])
            return
        else:
            await message.edit(content="Removendo...", components=[])
            ctx = response.ctx

    sound_wrapper.pop(key.lower())
    with open("sounds.json", "w") as file:
        json.dump(sound_wrapper, file)
    await ctx.send("Som removido com sucesso.")


@slash_command(name="soundboard", description="Abre uma soundboard.")
async def soundboard(ctx: SlashContext):
    keys: list[str] = list(sound_wrapper.keys())
    layout: list[ActionRow] = ActionRow.split_components(
        *[
            Button(
                label=keys[i],
                style=ButtonStyle.PRIMARY,
                custom_id=f"button_{keys[i]}",
            )
            for i in range(len(keys))
        ],
        count_per_row=4,
    )
    await ctx.send("Escolha um som:", components=layout)


@component_callback(pattern)
async def soundboard_callback(ctx: Component):
    await ctx.defer(edit_origin=True)
    await play_sound(ctx, sound_wrapper[ctx.custom_id[7:]])


async def play_sound(ctx: MessageCreate | ComponentContext, sound_url: str):
    author, channel = (
        (ctx.author, ctx.channel)
        if type(ctx) is ComponentContext
        else (ctx.message.author, ctx.message.channel)
    )

    if author == bot.user:
        return

    if sound_url:
        if author.voice:
            if connected:
                command_queue.append(sound_url)
                await channel.send(f"Seu som foi adicionado à fila, {author.mention}.")
            else:
                voice_state = await author.voice.channel.connect()
                await voice_state.play(AudioVolume(sound_url))
                if command_queue:
                    for command in command_queue:
                        await voice_state.play(AudioVolume(command))
                    command_queue.clear()
                await voice_state.disconnect()
        else:
            await channel.send(
                "Você precisa estar em um canal de voz para reproduzir sons."
            )


if __name__ == "__main__":
    with open("config.json", "r") as config:
        bot.start(json.load(config)["token"])
