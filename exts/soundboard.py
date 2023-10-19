import json
import re

from interactions import (
    ActionRow,
    Attachment,
    Button,
    ButtonStyle,
    ComponentContext,
    Extension,
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


class Soundboard(Extension):
    sound_wrapper: dict = {}
    command_queue: list = []
    connected = False
    pattern = re.compile(r"button_*")

    @listen()
    async def on_ready(self):
        print(f"{self.bot.user} está no ar!")
        try:
            with open("sounds.json", "r") as sounds:
                self.sound_wrapper = json.load(sounds)
        except FileNotFoundError:
            with open("sounds.json", "w") as sounds:
                json.dump({}, sounds)

    @listen()
    async def on_message_create(self, event: MessageCreate):
        if event.message.author == self.bot.user:
            return
        sound_url = self.sound_wrapper.get(event.message.content.lower())

        await self.play_sound(event, sound_url)

    @listen()
    async def on_voice_user_join(self, event: VoiceUserJoin):
        if event.author == self.bot.user:
            self.connected = True

    @listen()
    async def on_voice_user_leave(self, event: VoiceUserLeave):
        if event.author == self.bot.user:
            self.connected = False

    @slash_command(name="add_sound", description="Adiciona um som ao self.bot.")
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
    async def add_sound(self, ctx: SlashContext, key: str, sound: Attachment):
        guild_sounds = self.sound_wrapper.get(ctx.guild_id)
        if guild_sounds is None:
            self.sound_wrapper[ctx.guild_id] = {}
            guild_sounds = self.sound_wrapper.get(ctx.guild_id)
        if guild_sounds.get(key.lower()):
            layout: list[ActionRow] = [
                ActionRow(
                    Button(label="Sim", style=ButtonStyle.SUCCESS, custom_id="yes"),
                    Button(label="Não", style=ButtonStyle.DANGER, custom_id="no"),
                )
            ]
            message: Message = await ctx.send(
                "Esse som já existe. Deseja sobreescrever?", components=layout
            )
            response: Component = await self.bot.wait_for_component(
                messages=message, components=layout
            )
            if response.ctx.custom_id == "no":
                await message.edit(content="Operação cancelada.", components=[])
                return
            else:
                await message.edit(content="Sobreescrevendo...", components=[])
                ctx = response.ctx

        self.sound_wrapper[ctx.guild_id][key.lower()] = sound.url
        with open("sounds.json", "w") as file:
            json.dump(self.sound_wrapper, file)
        await ctx.send("Som adicionado com sucesso.")

    @slash_command(name="list_sounds", description="Lista todos os sons disponíveis.")
    async def list_sounds(self, ctx: SlashContext):
        sounds = "\n".join(self.sound_wrapper.keys())
        await ctx.send(f"Os sons disponíveis são:\n{sounds}")

    @slash_command(name="remove_sound", description="Remove um som do self.bot.")
    @slash_option(
        name="key",
        description="Palavra chave para o som.",
        opt_type=OptionType.STRING,
        required=True,
    )
    async def remove_sound(self, ctx: SlashContext, key: str):
        if self.sound_wrapper.get(ctx.guild_id).get(key.lower()):
            layout: list[ActionRow] = [
                ActionRow(
                    Button(label="Sim", style=ButtonStyle.SUCCESS, custom_id="yes"),
                    Button(label="Não", style=ButtonStyle.DANGER, custom_id="no"),
                )
            ]
            message: Message = await ctx.send(
                "Tem certeza que deseja remover esse som?", components=layout
            )
            response: Component = await self.bot.wait_for_component(
                messages=message, components=layout
            )
            if response.ctx.custom_id == "no":
                await message.edit(content="Operação cancelada.", components=[])
                return
            else:
                await message.edit(content="Removendo...", components=[])
                ctx = response.ctx

        self.sound_wrapper.get(ctx.guild_id).pop(key.lower())
        with open("sounds.json", "w") as file:
            json.dump(self.sound_wrapper, file)
        await ctx.send("Som removido com sucesso.")

    @slash_command(name="soundboard", description="Abre uma soundboard.")
    async def soundboard(self, ctx: SlashContext):
        guild_sounds = self.sound_wrapper.get(ctx.guild_id)
        if not guild_sounds:
            await ctx.send("Não há sons disponíveis.")
            return

        keys: list[str] = list(guild_sounds.keys())
        layout: list[ActionRow] = ActionRow.split_components(
            *[
                Button(
                    label=keys[i],
                    style=ButtonStyle.PRIMARY,
                    custom_id=f"button_{keys[i]}",
                )
                for i in range(len(keys))
            ],
            count_per_row=3,
        )
        await ctx.send("Escolha um som:", components=layout)

    @component_callback(pattern)
    async def soundboard_callback(self, ctx: Component):
        await ctx.defer(edit_origin=True)
        await self.play_sound(
            ctx, self.sound_wrapper.get(ctx.ctx.guild_id)[ctx.custom_id[7:]]
        )

    async def play_sound(self, ctx: MessageCreate | ComponentContext, sound_url: str):
        author, channel = (
            (ctx.author, ctx.channel)
            if type(ctx) is ComponentContext
            else (ctx.message.author, ctx.message.channel)
        )

        if author == self.bot.user:
            return

        if sound_url:
            if author.voice:
                if self.connected:
                    self.command_queue.append(sound_url)
                    await channel.send(
                        f"Seu som foi adicionado à fila, {author.mention}."
                    )
                else:
                    voice_state = await author.voice.channel.connect()
                    await voice_state.play(AudioVolume(sound_url))
                    if self.command_queue:
                        for command in self.command_queue:
                            await voice_state.play(AudioVolume(command))
                        self.command_queue.clear()
                    await voice_state.disconnect()
            else:
                await channel.send(
                    "Você precisa estar em um canal de voz para reproduzir sons."
                )
