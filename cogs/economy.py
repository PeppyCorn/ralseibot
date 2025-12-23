import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import random

BR_TZ = timezone(timedelta(hours=-3))

BOT_ECONOMY_ID = 0

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.col = bot.get_cog("XP").col
        
        self.col.update_one(
            {"_id": BOT_ECONOMY_ID},
            {"$setOnInsert": {"coins": 0}},
            upsert=True
        )

    # ------------------ DAILY ------------------
    @app_commands.command(name="daily", description="Colete suas moedas diárias")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now(BR_TZ)
        today = now.date()

        user = self.col.find_one({"_id": user_id})

        if user and "last_daily" in user:
            last_daily = user["last_daily"].astimezone(BR_TZ).date()
            if last_daily == today:
                return await interaction.response.send_message(
                    "❌ Você já coletou seu daily hoje!", ephemeral=True
                )

        coins = random.randint(1000, 3000)

        self.col.update_one(
            {"_id": user_id},
            {
                "$inc": {"coins": coins},
                "$set": {"last_daily": now}
            },
            upsert=True
        )

        await interaction.response.send_message(
            f"<:ralsei_love:1410029625358417952> Você coletou **{coins} ralcoins** no daily!"
        )


    # ------------------ BALANCE ------------------
    @app_commands.command(name="balance", description="Veja seu saldo")
    async def balance(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None
    ):
        if user is None:
            user = interaction.user
            user_id = user.id
            name = user.display_name
        elif user.bot:
            user_id = BOT_ECONOMY_ID
            name = "Ralsei"
        else:
            user_id = user.id
            name = user.display_name

        data = self.col.find_one({"_id": user_id}) or {}
        coins = data.get("coins", 0)

        rank = self.col.count_documents({
            "coins": {"$gt": coins}
        }) + 1

        await interaction.response.send_message(
            f"💳 **Saldo de {name}:** {coins} ralcoins\n"
            f"🏆 **Rank global:** #{rank}"
        )

        
        # ------------------ RANK GLOBAL ------------------
    async def build_coin_rank_embed(
        self,
        interaction: discord.Interaction,
        page: int,
        page_size: int
    ):
        skip = (page - 1) * page_size

        users = list(
            self.col.find(
                {"coins": {"$exists": True}},
                {"coins": 1}
            )
            .sort("coins", -1)
            .skip(skip)
            .limit(page_size)
        )

        if not users:
            return discord.Embed(
                title="🏦 Rank Global de Ralcoins",
                description="❌ Nenhum dado para esta página.",
                color=discord.Color.gold()
            )

        desc = ""
        for i, u in enumerate(users, start=skip + 1):
            user = interaction.client.get_user(u["_id"])
            name = user.display_name if user else f"Usuário {u['_id']}"
            desc += f"**#{i} {name}** — 💰 {u.get('coins', 0)} ralcoins\n"

        embed = discord.Embed(
            title="🏦 Rank Global de Ralcoins",
            description=desc,
            color=discord.Color.gold()
        )

        embed.set_footer(text=f"Página {page}")
        return embed


    async def build_coin_rank_embed(
        self,
        interaction: discord.Interaction,
        page: int,
        page_size: int
    ):
        skip = (page - 1) * page_size

        users = list(
            self.col.find(
                {"coins": {"$exists": True}},
                {"coins": 1}
            )
            .sort("coins", -1)
            .skip(skip)
            .limit(page_size)
        )

        if not users:
            return discord.Embed(
                title="🏦 Rank Global de Ralcoins",
                description="❌ Nenhum dado para esta página.",
                color=discord.Color.gold()
            )

        desc = ""
        for i, u in enumerate(users, start=skip + 1):
            user = interaction.client.get_user(u["_id"])
            name = user.display_name if user else f"Usuário {u['_id']}"
            desc += f"**#{i} {name}** — 💰 {u.get('coins', 0)} ralcoins\n"

        embed = discord.Embed(
            title="🏦 Rank Global de Ralcoins",
            description=desc,
            color=discord.Color.gold()
        )

        embed.set_footer(text=f"Página {page}")
        return embed
    
    async def get_coin_position(self, user_id: int) -> int | None:
        cursor = self.col.find(
            {"coins": {"$exists": True}},
            {"_id": 1}
        ).sort("coins", -1)

        for index, user in enumerate(cursor, start=1):
            if user["_id"] == user_id:
                return index

        return None

    async def build_rankcoins_embed(self, interaction, page: int, page_size: int = 5):
        skip = (page - 1) * page_size

        cursor = (
            self.col.find(
                {"coins": {"$exists": True}},
                {"coins": 1}
            )
            .sort("coins", -1)
            .skip(skip)
            .limit(page_size)
        )

        users = list(cursor)

        if not users:
            return None

        description = ""

        for i, user_data in enumerate(users, start=skip + 1):
            user_id = user_data["_id"]
            coins = user_data.get("coins", 0)

            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"Usuário {user_id}"

            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"

            description += f"**{i}. {medal} {name}** ➜ {coins} ralcoins\n"

        embed = discord.Embed(
            title="🏆 Rank Global de Ralcoins",
            description=description,
            color=discord.Color.gold()
        )

        embed.set_footer(text=f"Página {page}")

        return embed

      # ------------------ RANK GLOBAL ------------------
    @app_commands.command(name="rankcoins", description="Top 5 mais ricos do bot")
    async def rank(self, interaction: discord.Interaction):


        top = list(
            self.col.find(
                {"coins": {"$exists": True}},
                {"coins": 1}
            ).sort("coins", -1).limit(5)
        )

        if not top:
            return await interaction.response.send_message(
                "Ainda não há dados de economia 😢"
            )

        description = ""
        for i, user_data in enumerate(top, start=1):
            user_id = user_data["_id"]
            coins = user_data.get("coins", 0)

            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"Usuário {user_id}"

            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"

            description += f"**{i}. {medal} {name}** ➜ {coins} ralcoins\n"

        embed = discord.Embed(
            title="🏆 Rank Global de Ralcoins",
            description=description,
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))
