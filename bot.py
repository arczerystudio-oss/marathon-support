import os
import re
import discord
from discord import app_commands
from discord.ext import commands


TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ROLE_IDS = [int(x) for x in os.getenv("MOD_ROLE_IDS", "").split(",") if x.strip().isdigit()]
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))
TICKET_LOG_CHANNEL_ID = int(os.getenv("TICKET_LOG_CHANNEL_ID", "0"))
TICKET_BANNER_URL = os.getenv("TICKET_BANNER_URL", "").strip()
TICKET_PREFIX = "ticket"

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  

bot = commands.Bot(command_prefix="!", intents=intents)

def safe_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9_-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name[:20] if name else "user"


def is_mod(member: discord.Member) -> bool:
    if not MOD_ROLE_IDS:
        return False
    return any(r.id in MOD_ROLE_IDS for r in member.roles)


def get_opener_id_from_topic(channel: discord.TextChannel) -> int | None:
    if not channel.topic:
        return None
 
    prefix = "ticket_opener:"
    t = channel.topic.strip()
    if t.startswith(prefix):
        raw = t[len(prefix):].strip()
        if raw.isdigit():
            return int(raw)
    return None


async def log_ticket(
    guild: discord.Guild,
    *,
    action: str,
    opener: discord.Member | None,
    channel: discord.TextChannel | None,
    actor: discord.Member | None = None,
):
    if not TICKET_LOG_CHANNEL_ID:
        return
    log_ch = guild.get_channel(TICKET_LOG_CHANNEL_ID)
    if not isinstance(log_ch, discord.TextChannel):
        return

    embed = discord.Embed(
        title=f"SYS // TICKET {action}",
        color=0xB7FF00 if action == "CREATED" else 0xFF4D4D,
    )

    if opener:
        embed.add_field(name="Автор", value=f"{opener.mention}\n`{opener.id}`", inline=True)
    if actor:
        embed.add_field(name="Действие выполнил", value=f"{actor.mention}\n`{actor.id}`", inline=True)
    if channel:
        embed.add_field(name="Канал", value=f"{channel.mention}\n`{channel.id}`", inline=False)

    embed.set_footer(text="SYS // MARATHON СНГ — LOG")
    await log_ch.send(embed=embed)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return

        ch = interaction.channel
        if not isinstance(ch, discord.TextChannel):
            await interaction.response.send_message("Команда доступна только в текстовом канале.", ephemeral=True)
            return

        opener_id = get_opener_id_from_topic(ch)
        opener_member = interaction.guild.get_member(opener_id) if opener_id else None

        if opener_id is None:
       
            if not is_mod(interaction.user):
                await interaction.response.send_message("Нет прав закрыть этот тикет.", ephemeral=True)
                return
        else:
            if interaction.user.id != opener_id and not is_mod(interaction.user):
                await interaction.response.send_message("Нет прав закрыть этот тикет.", ephemeral=True)
                return

        await interaction.response.send_message("SYS // TICKET CLOSING", ephemeral=True)

   
        await log_ticket(
            interaction.guild,
            action="CLOSED",
            opener=opener_member,
            actor=interaction.user,
            channel=ch,
        )

        try:
            await ch.send("SYS // TICKET CLOSED")
        except Exception:
            pass

        try:
            await ch.delete(reason=f"Ticket closed by {interaction.user} ({interaction.user.id})")
        except Exception as e:
            try:
                await interaction.followup.send(f"Не смог удалить канал: {e}", ephemeral=True)
            except Exception:
                pass


class TicketOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Создать тикет", style=discord.ButtonStyle.success, custom_id="ticket:create")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            return

   
        for ch in guild.text_channels:
            if ch.topic and ch.topic.strip() == f"ticket_opener:{interaction.user.id}":
                await interaction.response.send_message(f"У тебя уже есть тикет: {ch.mention}", ephemeral=True)
                return

     
        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        if category is not None and not isinstance(category, discord.CategoryChannel):
            category = None

       
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
        }

        for rid in MOD_ROLE_IDS:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel_name = f"{TICKET_PREFIX}-{safe_name(interaction.user.name)}"

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"ticket_opener:{interaction.user.id}",
                reason=f"Ticket created by {interaction.user} ({interaction.user.id})",
            )
        except discord.Forbidden:
            await interaction.response.send_message("У бота нет прав создавать каналы/выдавать доступ.", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"Ошибка создания тикета: {e}", ephemeral=True)
            return

        await interaction.response.send_message(f"Тикет создан: {ticket_channel.mention}", ephemeral=True)

        await ticket_channel.send(
            f"SYS // TICKET OPEN\n"
            f"Автор: {interaction.user.mention}\n"
            f"Опиши вопрос/жалобу одним сообщением. Доступ видят только ты и модерация."
        )
        await ticket_channel.send("SYS // MOD PANEL", view=TicketControlView())

    
        await log_ticket(
            guild,
            action="CREATED",
            opener=interaction.user,
            actor=interaction.user,
            channel=ticket_channel,
        )


@bot.event
async def on_ready():
    print(f"READY: {bot.user}", flush=True)


    bot.add_view(TicketOpenView())
    bot.add_view(TicketControlView())

    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Sync error: {e}", flush=True)

@bot.tree.command(name="ticket_panel", description="Отправить SYSTEM NOTICE панель тикетов в этот канал")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="SYSTEM NOTICE // ТИКЕТЫ",
        description=(
            "Если возник **вопрос**, **жалоба** или нужен **вызов модерации** - откройте тикет.\n\n"
            "• Нажмите **Создать тикет**\n"
            "• Опишите ситуацию одним сообщением\n"
        ),
        color=0xB7FF00,
    )

    embed.add_field(
        name="Важно",
        value="Флуд и ложные обращения - нарушение правил сервера.",
        inline=False,
    )

    if TICKET_BANNER_URL.startswith(("http://", "https://")):
        embed.set_image(url=TICKET_BANNER_URL)

    embed.set_footer(text="SYS // MARATHON СНГ — SERVER ONLINE")

    await interaction.channel.send(embed=embed, view=TicketOpenView())
    await interaction.response.send_message("Панель тикетов отправлена.", ephemeral=True)


@ticket_panel.error
async def ticket_panel_error(interaction: discord.Interaction, error):
    try:
        await interaction.response.send_message("Нет прав.", ephemeral=True)
    except Exception:
        pass


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN не задан")

if not TICKET_LOG_CHANNEL_ID:
    print("WARN: TICKET_LOG_CHANNEL_ID не задан — логирование отключено.", flush=True)

bot.run(TOKEN)
