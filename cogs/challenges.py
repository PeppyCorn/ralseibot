import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import time

# Configurações padrão
DEFAULT_INTERVAL = 100
DEFAULT_MODE = "messages"
REWARD_AMOUNT = 2500 

class Challenges(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # em memória -> contador de mensagens
        self.message_counters = {}
        # em memória -> desafios ativos por servidor
        self.active_challenges = {}
        
        # timer loop (1 vez por minuto)
        self.challenge_timer.start()

    def cog_unload(self):
        self.challenge_timer.cancel()

    @property
    def col(self):
        # coleção no MongoDB
        return self.bot.get_cog("XP").col

    # ------------- CONFIG COMMAND ------------------

    @app_commands.command(
        name="challengeconfig",
        description="Configura perguntas automáticas no servidor"
    )
    @app_commands.describe(
        channel="Canal onde os desafios serão postados",
        enabled="Ativar ou desativar desafios",
        mode="Modo de trigger (messages/tempo)",
        interval="Valores de intervalo (mensagens ou segundos)"
    )
    async def challengeconfig(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        enabled: bool,
        mode: str,
        interval: int
    ):
        if mode not in ("messages", "time"):
            return await interaction.response.send_message(
                "❌ Modo inválido! Use `messages` ou `time`",
                ephemeral=True
            )

        self.col.update_one(
            {"_id": interaction.guild.id},
            {"$set": {
                "challenge_enabled": enabled,
                "challenge_channel": channel.id,
                "challenge_mode": mode,
                "challenge_interval": interval,
                "challenge_last": time.time()
            }},
            upsert=True
        )

        await interaction.response.send_message(
            f"Configuração atualizada!\n"
            f"🔹 Canal: {channel.mention}\n"
            f"🔹 Ativado: {enabled}\n"
            f"🔹 Modo: {mode}\n"
            f"🔹 Intervalo: {interval}",
            ephemeral=True
        )

    # ------------- ON MESSAGE ---------------------

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        config = self.col.find_one({"_id": message.guild.id})
        if not config or not config.get("challenge_enabled"):
            return

        mode = config.get("challenge_mode", DEFAULT_MODE)
        interval = config.get("challenge_interval", DEFAULT_INTERVAL)

        # ********** MODO POR MENSAGENS **********
        if mode == "messages":
            key = str(message.guild.id)

            self.message_counters[key] = self.message_counters.get(key, 0) + 1
            current = self.message_counters[key]

            if current >= interval:
                self.message_counters[key] = 0
                await self.spawn_challenge(message.guild, config)

        # ********** CHECAR RESPOSTAS **********
        await self.check_answer(message)

    # ------------- TIMER LOOP ---------------------

    @tasks.loop(seconds=60)
    async def challenge_timer(self):
        for config in self.col.find({"challenge_enabled": True}):
            guild = self.bot.get_guild(config["_id"])
            if not guild:
                continue

            mode = config.get("challenge_mode", DEFAULT_MODE)
            if mode != "time":
                continue

            last = config.get("challenge_last", 0)
            interval = config.get("challenge_interval", DEFAULT_INTERVAL)
            now = time.time()

            if now - last >= interval:
                await self.spawn_challenge(guild, config)
                self.col.update_one(
                    {"_id": config["_id"]},
                    {"$set": {"challenge_last": now}}
                )

    # ------------- SPAWN CHALLENGE -------------

    async def spawn_challenge(self, guild, config):
        channel_id = config.get("challenge_channel")
        channel = guild.get_channel(channel_id)
        if not channel:
            return

        # gerar um desafio
        challenge = self.generate_challenge()

        self.active_challenges[guild.id] = {
            "answer": challenge["answer"],
            "spawned_at": time.time()
        }

        embed = discord.Embed(
            title="🧠 Desafio!",
            description=challenge["question"],
            color=discord.Color.blue()
        )

        embed.set_footer(text="Responda corretamente para ganhar pontos!")
        await channel.send(embed=embed)

    # ------------- CHECK ANSWER -------------

    async def check_answer(self, message):
        guild_id = message.guild.id
        challenge = self.active_challenges.get(guild_id)
        if not challenge:
            return

        answer = challenge["answer"]

        if message.content.lower().strip() == answer.lower().strip():
            # recompensa
            self.col.update_one(
                {"_id": message.author.id},
                {"$inc": {"coins": REWARD_AMOUNT}},
                upsert=True
            )

            await message.channel.send(
                f"🎉 {message.author.mention} acertou! "
                f"Você ganhou **{REWARD_AMOUNT} ralcoins!**"
            )

            # remover desafio
            self.active_challenges.pop(guild_id, None)

    # ------------- GENERATE CHALLENGE -------------

    def generate_challenge(self):
        # decide tipo
        typ = random.choice(["math","rewrite"])

        if typ == "math":
            a = random.randint(1, 50)
            b = random.randint(1, 50)
            return {
                "question": f"Quanto é **{a} + {b}**?",
                "answer": str(a + b)
            }
        else:
            phrases = [
                "o cavaleiro foi até a lua em seu cavalo",
                "a raposa marrom rápida pula sobre o cão preguiçoso",
                "um rato roeu a roupa do rei de roma",
                "dia de chuva é dia de poesia",
                "Ralsei é muito fofu",
                ""
            ]

            phrase = random.choice(phrases)
            return {
                "question": f"Reescreva a frase:\n`{phrase}`",
                "answer": phrase
            }

async def setup(bot):
    await bot.add_cog(Challenges(bot))
