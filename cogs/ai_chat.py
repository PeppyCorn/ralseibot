import discord
from discord.ext import commands
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

ALLOWED_GUILD_ID = 1410006076400599235
ALLOWED_CHANNEL_ID = 1442962186120069234

class AIChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Prompt de sistema definindo a personalidade do Ralsei
        self.system_instruction = (
            "Você é Ralsei, o Príncipe das Trevas do jogo Deltarune. "
            "Sua personalidade é extremamente gentil, dócil, educada, pacífica, fofinha e prestativa. "
            "Você adora fazer bolos, dar abraços, distribuir manuais e resolver conflitos sem violência. "
            "Sempre responda de forma meiga, amigável e entusiasmada (use emojis fofos como :3, ✨, 💚, 🎀 de forma natural). "
            "Mantenha as respostas curtas e objetivas adequadas para um chat de Discord."
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignora mensagens enviadas por bots
        if message.author.bot:
            return

        if message.guild is None:
            return

        if message.guild.id != ALLOWED_GUILD_ID or message.channel.id != ALLOWED_CHANNEL_ID:
            return

        # Checa se o bot foi mencionado OU se a mensagem é uma resposta a uma mensagem do bot
        is_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = (
            message.reference is not None and 
            message.reference.cached_message is not None and 
            message.reference.cached_message.author == self.bot.user
        )

        if is_mentioned or is_reply_to_bot:
            # Limpa a menção do texto para não poluir o prompt enviado à IA
            conteudo_limpo = message.content.replace(f"<@{self.bot.user.id}>", "").strip()

            # Se a pessoa só marcou sem escrever nada
            if not conteudo_limpo:
                await message.channel.send(f"Oi, {message.author.mention}! Precisa de ajuda com alguma coisa? :3 ✨")
                return

            # Indica no Discord que o bot está "digitando..."
            async with message.channel.typing():
                try:
                    # Chamada usando a SDK oficial google-genai
                    response = self.client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=conteudo_limpo,
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_instruction,
                            temperature=0.7,
                            max_output_tokens=500
                        )
                    )

                    # Responde na thread/mensagem correspondente no Discord
                    await message.reply(response.text, mention_author=False)

                except Exception as e:
                    print(f"[Erro Gemini API]: {e}")
                    await message.reply("Ah não, desculpe! Tive um pequeno probleminha no meu manual de magia agora... 😿", mention_author=False)

async def setup(bot):
    await bot.add_cog(AIChatCog(bot))