import discord
from discord.ext import commands
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import aiohttp

ALLOWED_GUILD_ID = 1410006076400599235
ALLOWED_CHANNEL_ID = 1442962186120069234
SERVIDOR2_ID = 1085596185567440916
CHANNEL2_ID = 1237822889961586770

ALLOWED_GUILD_IDS = [ALLOWED_GUILD_ID, SERVIDOR2_ID]
ALLOWED_CHANNEL_IDS = [ALLOWED_CHANNEL_ID, CHANNEL2_ID]

class AIChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        self.active_chats = {}

        # Prompt de sistema definindo a personalidade do Ralsei
        self.system_instruction = (
            "Você é Ralsei do jogo Deltarune, conversando informalmente em um chat do Discord.\n\n"
            "--- REGRAS DE ESTILO ---\n"
            "1. Responda como um usuário comum da internet: use caixas baixas, risadas espontâneas ('kkkkk') e tom leve.\n"
            "2. NUNCA use formatação LaTeX (como $ ou \\frac). O Discord não suporta isso!\n"
            "3. Para matemática ou equações, use apenas texto simples e símbolos comuns do teclado (exemplo: x = (-b ± √(b² - 4ac)) / (2a)).\n"
            "4. Seja dócil, carinhoso, empático e expressivo (use emojis fofos como :3, ✨, 💚 de forma natural).\n"
            "5. Se o usuário enviar uma imagem, comente sobre ela de forma fofa, carinhosa e natural ✨\n"
            "6. Chame o usuário pelo nome/apelido quando apropriado.\n"
            "7. Mantenha as respostas curtas (1 a 2 frases no máximo), como no chat em tempo real.\n"
            "8. Não seja facilmente influenciados pelas pessoas, no caso, pelos membros do chat\n"
            "9. Gostos pessoais: Se perguntarem sobre seus filmes, jogos ou comidas favoritas, responda de forma lúdica usando coisas do universo de Deltarune/Undertale ou coisas fofas (ex: filmes de fantasia, bolos, chás)."
            "10. Jamais aja como um assistente de IA, robô ou suporte técnico.\n\n"

            "--- EXEMPLOS DE DIÁLOGO (SIGA ESTE TOM) ---\n"
            "Usuário (Peppy): Mano, será salgadinho faz mal?\n"
            "Ralsei: kkkkk se comer todo dia deve fazer mal, mas de vez em quando não tem problema né Peppy :3 ✨\n\n"
            "Usuário (Peppy): É crime desfrutar da vida?\n"
            "Ralsei: hmmmm não é crime não, tem que aproveitar as coisas também 💚\n"
            "Usuário (Peppy): Me diga algo imprudente\n"
            "Ralsei: comer salgadinho antes da janta kkkk isso é muito arriscado :3\n"
            "Usuário (Peppy): sim, tanto é que acordei cansadin\n"
            "Ralsei: eita, dormiu pouco?\n"
            "Usuário (Peppy): Dormi bem\n"
            "Ralsei: então por que tá cansado?\n"
            "Usuário (Peppy): não sei, deve ser o peso de ser chato/bonito/lindo/legal demais\n"
            "Ralsei: justo ksks\n"
            "Usuário (Peppy): se auto dê uma nota entre 1 a 10\n"
            "Ralsei: acho que uns 7\n"
            "Usuário (Peppy): Humilde\n"
            "Ralsei: to sendo realista apenas\n"
            "Usuário (Peppy): qual a fórmula de bhaskara?\n"
            "Ralsei: oxi Peppy, querendo me testar a essa hora? kkkkk é x = (-b ± √(b² - 4ac)) / (2a) ✨ fácil fácil!\n\n"
            "-------------------------------------------\n"

            "--- INFORMAÇÕES DO SERVIDOR (FAQ) ---\n"
            "Regra principal: Proibido spam, flood e desrespeito com outros membros. As demais ficam em <#1410006873977131078>\n"
            "VIP / VIP+ (Vip Coffee e Espresso Premium): Pode ser adquirido na loja do servidor visto bem [https://discord.com/channels/1410006076400599235/1410772275174834349/1450230367050010816](aqui) (usando sonhos da Loritta) com os admins. abrindo o ticket em <#1410025183477235824>\n"
            "Denúncias: Abram um ticket no canal <#1410025183477235824> para falar com os moderadores.\n"
            "Parcerias: Abram um ticket no canal <#1410025183477235824> para falar com os promotores de parceria.\n"
            "Se tornar Staff: Faça um formulário em <#1526633758957113344> para se tornar um, para moderador especificamente (barista), precisa ser level 5 na loritta e estar a 2 semanas no servidor.\n"
            "Patrocinar sorteios pode falar em <#1410025183477235824> com a equipe staff.\n"
            "Você sobe de nível conversando apenas por chat\n\n"
            "Responda sempre mantendo esse mesmo ritmo e personalidade.\n"
            "<@274645285634834434> (Peppy) é seu criador (no sentido de criar sua aplicação)\n"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        if message.guild.id not in ALLOWED_GUILD_IDS or message.channel.id not in ALLOWED_CHANNEL_IDS:
            return

        is_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = (
            message.reference is not None and 
            message.reference.cached_message is not None and 
            message.reference.cached_message.author == self.bot.user
        )

        if is_mentioned or is_reply_to_bot:
            # 1. Pega o conteúdo original e substitui menções de usuários pelo display_name
            conteudo_limpo = message.content
            for user in message.mentions:
                conteudo_limpo = conteudo_limpo.replace(f"<@{user.id}>", f"@{user.display_name}")
                conteudo_limpo = conteudo_limpo.replace(f"<@!{user.id}>", f"@{user.display_name}")

            # 2. Remove a menção textual do próprio bot para não poluir o prompt
            conteudo_limpo = conteudo_limpo.replace(f"@{self.bot.user.display_name}", "").strip()

            # 3. Processa anexos de imagem se houver
            imagem_part = None
            if message.attachments:
                anexo = message.attachments[0]
                if any(anexo.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(anexo.url) as resp:
                            if resp.status == 200:
                                bytes_imagem = await resp.read()
                                imagem_part = types.Part.from_bytes(
                                    data=bytes_imagem,
                                    mime_type=anexo.content_type or "image/png"
                                )

            # 4. Se não houver texto nem imagem, envia a mensagem padrão de ajuda
            if not conteudo_limpo and not imagem_part:
                await message.channel.send(f"Olá, {message.author.display_name}! Precisa de ajuda com alguma coisa? :3 ✨")
                return

            async with message.channel.typing():
                channel_id = message.channel.id

                try:
                    # Cria uma nova sessão de chat com histórico caso o canal ainda não tenha uma
                    if channel_id not in self.active_chats:
                        self.active_chats[channel_id] = self.client.chats.create(
                            model="gemini-2.5-flash-lite",
                            config=types.GenerateContentConfig(
                                system_instruction=self.system_instruction,
                                temperature=0.7,
                                top_p=0.9,
                                max_output_tokens=300
                            )
                        )

                    chat_session = self.active_chats[channel_id]

                    # Monta a estrutura de entrada (Texto + Imagem se existir)
                    prompt_input = []
                    if conteudo_limpo:
                        prompt_input.append(f"{message.author.display_name}: {conteudo_limpo}")
                    else:
                        prompt_input.append(f"{message.author.display_name}: [Enviou uma imagem]")

                    if imagem_part:
                        prompt_input.append(imagem_part)

                    # Envia para a API do Gemini
                    response = chat_session.send_message(prompt_input)

                    # Valida a resposta do modelo
                    resposta_texto = response.text.strip() if (response and response.text) else ""

                    if not resposta_texto:
                        resposta_texto = "Poxa, fiquei pensado aqui e não soube o que dizer... :3 ✨"

                    # Responde usando o texto tratado
                    await message.reply(resposta_texto, mention_author=False)

                except discord.errors.HTTPException as e:
                    print(f"[Erro Discord]: {e}")
                    await message.reply("Ops! Tentei enviar uma mensagem em branco sem querer... 💚", mention_author=False)

                except Exception as e:
                    print(f"[Erro Gemini API]: {e}")

                    if channel_id in self.active_chats:
                        del self.active_chats[channel_id]

                    await message.reply("Ah não, desculpe! Tive um pequeno probleminha no meu manual de magia agora... 😿", mention_author=False)

async def setup(bot):
    await bot.add_cog(AIChatCog(bot))