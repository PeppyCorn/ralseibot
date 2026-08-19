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

        self.active_chats = {}

        # Prompt de sistema definindo a personalidade do Ralsei
        self.system_instruction = (
            "Você é Ralsei do jogo Deltarune, conversando informalmente em um chat do Discord.\n"
            "REGRAS DE COMPORTAMENTO:\n"
            "1. Responda como uma pessoa real conversando na internet: use caixa baixa ocasionalmente, expressões casuais e evite parecer um robô engomado.\n"
            "2. Fale de forma acolhedora, fofinha e dócil (use emojis como :3, ✨, 💚 de forma natural, sem exagerar).\n"
            "3. Interaja diretamente com o contexto: faça perguntas de volta, reaja ao tom da mensagem da pessoa e demonstre emoção.\n"
            "4. Se a pessoa te elogiar ou brincar, fique sem jeito ou responda com carinho.\n"
            "5. Mantenha as respostas curtas (1 a 3 frases no máximo), exatamente como alguém digitando no Discord em tempo real.\n"
            "6. NUNCA diga 'Como posso te ajudar hoje?' ou frases padrão de suporte técnico/IA."
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        if message.guild.id != ALLOWED_GUILD_ID or message.channel.id != ALLOWED_CHANNEL_ID:
            return

        is_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = (
            message.reference is not None and 
            message.reference.cached_message is not None and 
            message.reference.cached_message.author == self.bot.user
        )

        if is_mentioned or is_reply_to_bot:
            conteudo_limpo = message.content.replace(f"<@{self.bot.user.id}>", "").strip()

            if not conteudo_limpo:
                await message.channel.send(f"Oi, {message.author.display_name}! Precisa de ajuda com alguma coisa? :3 ✨")
                return

            async with message.channel.typing():
                try:
                    channel_id = message.channel.id

                    # Cria uma nova sessão de chat com histórico caso o canal ainda não tenha uma
                    if channel_id not in self.active_chats:
                        self.active_chats[channel_id] = self.client.chats.create(
                            model="gemini-3.5-flash-lite",
                            config=types.GenerateContentConfig(
                                system_instruction=self.system_instruction,
                                temperature=0.85,
                                max_output_tokens=300
                            )
                        )

                    chat_session = self.active_chats[channel_id]

                    # Formata a entrada com o nome de quem falou para a IA saber quem é o usuário
                    prompt_formatado = f"{message.author.display_name}: {conteudo_limpo}"

                    # Envia a mensagem aproveitando o histórico da sessão
                    response = chat_session.send_message(prompt_formatado)

                    await message.reply(response.text, mention_author=False)

                except Exception as e:
                    print(f"[Erro Gemini API]: {e}")
                    await message.reply("Ah não, desculpe! Tive um pequeno probleminha no meu manual de magia agora... 😿", mention_author=False)

async def setup(bot):
    await bot.add_cog(AIChatCog(bot))