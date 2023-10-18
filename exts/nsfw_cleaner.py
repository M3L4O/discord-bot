import json

from interactions import (
    Extension,
    GuildChannel,
    IntervalTrigger,
    OptionType,
    SlashContext,
    Task,
    User,
    listen,
    slash_command,
    slash_option,
)


class NSFWCleaner(Extension):
    @listen()
    async def on_ready(self):
        self.clean_nsfw.start()
        try:
            with open("nsfw.json", "r") as nsfw:
                data = json.load(nsfw)
                self.users_ids = data["users"]
                self.channels_ids = data["channels"]

        except FileNotFoundError:
            self.users_ids = []
            self.channels_ids = []
            with open("nsfw.json", "w") as nsfw:
                json.dump({"users": [], "channels": []}, nsfw)

    @Task.create(IntervalTrigger(hours=6))
    async def clean_nsfw(self):
        print("Limpando o NSFW...")
        for channel_id in self.channels_ids:
            channel = self.bot.get_channel(channel_id)
            await channel.purge(
                deletion_limit=100,
                predicate=lambda message: message.author.id in self.users_ids,
            )

    @slash_command(description="Adiciona canal onde funcionará o NSFW Cleaner.")
    @slash_option(
        name="channel",
        description="Canal onde funcionará o NSFW cleaner",
        required=True,
        opt_type=OptionType.CHANNEL,
    )
    async def add_nsfw_channel(self, ctx: SlashContext, channel: GuildChannel):
        self.channels_ids.append(channel.id)
        with open("nsfw.json", "w") as nsfw:
            json.dump({"users": self.users_ids, "channels": self.channels_ids}, nsfw)
        await channel.send("Canal adicionado com sucesso!")

    @slash_command(description="Adicionar que manda NSFW ao NSFW Cleaner.")
    @slash_option(
        name="user",
        description="Usuário que manda NSFW",
        required=True,
        opt_type=OptionType.USER,
    )
    async def add_nsfw_sender(self, ctx: SlashContext, user: User):
        self.users_ids.append(user.id)
        with open("nsfw.json", "w") as nsfw:
            json.dump({"users": self.users_ids, "channels": self.channels_ids}, nsfw)
        await ctx.send("Usuário adicionado com sucesso!")
