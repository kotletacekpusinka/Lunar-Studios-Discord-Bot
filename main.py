import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", 0))
CATEGORY_ID = int(os.getenv("CATEGORY_ID", 0))
GUILD_ID = int(os.getenv("GUILD_ID", 0))

intents = discord.Intents.default()
intents.guilds = True


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket", 
        style=discord.ButtonStyle.danger, 
        emoji="🔒", 
        custom_id="close_ticket_btn"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("This ticket will be deleted in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except discord.NotFound:
            pass


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket", 
        style=discord.ButtonStyle.primary, 
        emoji="📩", 
        custom_id="create_ticket_btn"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        safe_name = "".join(c for c in user.name.lower() if c.isalnum() or c in "-_")
        channel_name = f"ticket-{safe_name}"

        # Prevent duplicate tickets
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(
                f"You already have an open ticket in {existing_channel.mention}!", 
                ephemeral=True
            )
            return

        category = guild.get_channel(CATEGORY_ID) if CATEGORY_ID else None
        staff_role = guild.get_role(STAFF_ROLE_ID)

        # Set private channel permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, 
                send_messages=True, 
                attach_files=True, 
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, 
                send_messages=True, 
                manage_channels=True
            )
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, 
                send_messages=True, 
                attach_files=True, 
                read_message_history=True
            )

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"Support Ticket | {user.name}",
            description=(
                "Welcome to **Lunar Studios** Support!\n\n"
                "Please describe your issue, bug report, or commission details below.\n"
                "Our team will be with you shortly.\n\n"
                "Click the button below when you are ready to close this ticket."
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="Lunar Studios | Ticket System")

        mention_text = f"{user.mention}"
        if staff_role:
            mention_text += f" | {staff_role.mention}"

        await ticket_channel.send(content=mention_text, embed=embed, view=CloseTicketView())
        await interaction.response.send_message(
            f"Your ticket has been created: {ticket_channel.mention}", 
            ephemeral=True
        )


class LunarBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Persistent buttons survive bot restarts
        self.add_view(TicketPanelView())
        self.add_view(CloseTicketView())

        # Sync slash commands
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
        else:
            await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} for Lunar Studios!")


bot = LunarBot()

@bot.tree.command(name="ticket-panel", description="Deploy the Lunar Studios ticket panel")
@app_commands.default_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌙 Lunar Studios | Support & Commissions",
        description=(
            "Need help with one of our games, want to report a bug, or discuss a commission?\n\n"
            "Click the button below to open a private ticket with our staff!"
        ),
        color=0x5865F2
    )
    embed.set_footer(text="Lunar Studios Support System")

    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message("Ticket panel successfully sent.", ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN)
