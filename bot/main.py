import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, timedelta
import os
import sys

# Add the bot directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database
from config import *

# Custom Discord logging handler
class DiscordLogHandler(logging.Handler):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.log_channel = None
        
    async def setup_channel(self):
        """Find or create the log channel"""
        if not self.bot.guilds:
            return
            
        guild = self.bot.guilds[0]  # Use first guild
        
        # Find admin category
        admin_category = discord.utils.get(guild.categories, name=ADMIN_CATEGORY)
        if not admin_category:
            # Create admin category if it doesn't exist
            admin_category = await guild.create_category(
                name=ADMIN_CATEGORY,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
            )
        
        # Find or create log channel
        self.log_channel = discord.utils.get(guild.channels, name=LOG_CHANNEL)
        if not self.log_channel:
            self.log_channel = await guild.create_text_channel(
                name=LOG_CHANNEL,
                category=admin_category,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
            )
    
    def emit(self, record):
        """Send log record to Discord channel"""
        if not ENABLE_DISCORD_LOGGING or not self.log_channel:
            return
            
        if record.levelname not in LOG_LEVELS_TO_DISCORD:
            return
            
        # Format the log message
        log_msg = self.format(record)
        
        # Create embed based on log level
        color = {
            'ERROR': discord.Color.red(),
            'WARNING': discord.Color.orange(),
            'INFO': discord.Color.blue(),
            'DEBUG': discord.Color.light_grey()
        }.get(record.levelname, discord.Color.dark_grey())
        
        embed = discord.Embed(
            title=f"{record.levelname} Log",
            description=f"```\n{log_msg}\n```",
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Module", value=record.name, inline=True)
        embed.add_field(name="Function", value=record.funcName or "N/A", inline=True)
        embed.add_field(name="Line", value=record.lineno, inline=True)
        
        # Send to Discord (async)
        asyncio.create_task(self._send_to_discord(embed))
    
    async def _send_to_discord(self, embed):
        """Async method to send embed to Discord"""
        try:
            if self.log_channel:
                await self.log_channel.send(embed=embed)
        except Exception as e:
            # Don't log Discord logging errors to avoid recursion
            print(f"Failed to send log to Discord: {e}")

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOGGING_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot setup with intents (all privileged intents enabled in Discord portal)
intents = discord.Intents.default()
intents.message_content = True  # Enabled - required for bot commands
intents.members = True          # Enabled - for member events and info
intents.guilds = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# Initialize database
db = Database()

# Initialize Discord logging handler
discord_handler = DiscordLogHandler(bot)
discord_handler.setLevel(getattr(logging, LOGGING_LEVEL))
discord_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Add Discord handler to root logger
if ENABLE_DISCORD_LOGGING:
    logging.getLogger().addHandler(discord_handler)

# Global variable for message logging channel
message_log_channel = None

# Global variable for member count channel
member_count_channel = None

async def setup_message_logging_channel():
    """Set up the message logging channel"""
    global message_log_channel
    
    if not bot.guilds:
        return
        
    guild = bot.guilds[0]  # Use first guild
    
    # Find admin category
    admin_category = discord.utils.get(guild.categories, name=ADMIN_CATEGORY)
    if not admin_category:
        # Create admin category if it doesn't exist
        admin_category = await guild.create_category(
            name=ADMIN_CATEGORY,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )
    
    # Find or create message log channel
    message_log_channel = discord.utils.get(guild.channels, name=MESSAGE_LOG_CHANNEL)
    if not message_log_channel:
        message_log_channel = await guild.create_text_channel(
            name=MESSAGE_LOG_CHANNEL,
            category=admin_category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )
        
    logger.info(f"Message logging channel set up: #{message_log_channel.name}")

async def setup_member_count_channel():
    """Set up the member count channel in General category"""
    global member_count_channel
    
    if not bot.guilds:
        return
        
    guild = bot.guilds[0]  # Use first guild
    
    # Find or create General category
    general_category = discord.utils.get(guild.categories, name=GENERAL_CATEGORY)
    if not general_category:
        # Create General category if it doesn't exist
        general_category = await guild.create_category(
            name=GENERAL_CATEGORY,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, connect=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
        )
    
    # Find or create member count channel
    member_count_channel = None
    for channel in guild.channels:
        if channel.name.startswith(MEMBER_COUNT_CHANNEL):
            member_count_channel = channel
            break
    if not member_count_channel:
        # Create the channel with initial member count
        member_count = len(guild.members)
        channel_name = f"{MEMBER_COUNT_CHANNEL}-{member_count}"
        
        member_count_channel = await guild.create_text_channel(
            name=channel_name,
            category=general_category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
        )
        
        # Send welcome message to the channel
        embed = discord.Embed(
            title="📊 Server Member Count",
            description=f"This channel displays the current number of members in **{guild.name}**.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Current Members", value=f"**{member_count}** members", inline=False)
        embed.add_field(name="Note", value="This channel is read-only and updates automatically when members join or leave.", inline=False)
        embed.set_footer(text=f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        await member_count_channel.send(embed=embed)
    else:
        # Update existing channel name if needed
        await update_member_count_channel()
        
    logger.info(f"Member count channel set up: #{member_count_channel.name}")

async def update_member_count_channel():
    """Update the member count channel name with current member count"""
    global member_count_channel
    
    if not member_count_channel or not bot.guilds:
        return
    
    try:
        guild = bot.guilds[0]
        member_count = len(guild.members)
        new_channel_name = f"{MEMBER_COUNT_CHANNEL}-{member_count}"
        
        # Only update if the name is different
        if member_count_channel.name != new_channel_name:
            await member_count_channel.edit(name=new_channel_name)
            logger.info(f"Updated member count channel name to: {new_channel_name}")
            
    except Exception as e:
        logger.error(f"Error updating member count channel: {e}")

async def log_user_message(message):
    """Log user message to the message logging channel"""
    global message_log_channel
    
    if not message_log_channel:
        return
    
    try:
        # Create embed for the message log
        embed = discord.Embed(
            color=discord.Color.blue(),
            timestamp=message.created_at
        )
        
        # Set author info
        embed.set_author(
            name=f"{message.author.display_name} ({message.author})",
            icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
        )
        
        # Add message content
        content = message.content if message.content else "*[No text content]*"
        if len(content) > 1024:
            content = content[:1021] + "..."
        embed.add_field(name="Message", value=content, inline=False)
        
        # Add channel info
        embed.add_field(name="Channel", value=f"#{message.channel.name}", inline=True)
        embed.add_field(name="User ID", value=str(message.author.id), inline=True)
        embed.add_field(name="Message ID", value=str(message.id), inline=True)
        
        # Add attachments info if any
        if message.attachments:
            attachment_info = []
            for attachment in message.attachments:
                attachment_info.append(f"[{attachment.filename}]({attachment.url})")
            embed.add_field(
                name="Attachments", 
                value="\n".join(attachment_info[:5]), # Limit to 5 attachments
                inline=False
            )
        
        # Add embeds info if any
        if message.embeds:
            embed.add_field(name="Embeds", value=f"{len(message.embeds)} embed(s)", inline=True)
        
        # Add reactions info if any
        if message.reactions:
            reactions = [f"{reaction.emoji}({reaction.count})" for reaction in message.reactions[:5]]
            embed.add_field(name="Reactions", value=" ".join(reactions), inline=True)
        
        # Set footer
        embed.set_footer(text=f"Guild: {message.guild.name}")
        
        # Send to message log channel
        await message_log_channel.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error logging message: {e}")

@bot.event
async def on_ready():
    """Event triggered when bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Set up Discord logging channel
    if ENABLE_DISCORD_LOGGING:
        await discord_handler.setup_channel()
        logger.info("Discord logging channel set up successfully!")
    
    # Set up message logging channel
    await setup_message_logging_channel()
    
    # Set up member count channel
    await setup_member_count_channel()
    
    # Set bot status
    activity = discord.Activity(type=discord.ActivityType.watching, name="the server | !help")
    await bot.change_presence(activity=activity)

@bot.event
async def on_member_join(member):
    """Welcome new members"""
    try:
        # Store user join data
        db.store_user_join(
            user_id=member.id,
            username=str(member),
            guild_id=member.guild.id,
            join_date=member.joined_at or datetime.utcnow()
        )
        
        # Send welcome message
        welcome_channel = discord.utils.get(member.guild.channels, name=WELCOME_CHANNEL)
        if welcome_channel:
            embed = discord.Embed(
                title="Welcome to the server! 🎉",
                description=f"Hey {member.mention}! Welcome to **{member.guild.name}**!",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Getting Started",
                value=f"• Check out #{RULES_CHANNEL} for server rules\n• Use `!help` to see available commands\n• Use `!role <role_name>` to request roles",
                inline=False
            )
            embed.add_field(
                name="Available Roles",
                value=", ".join(AVAILABLE_ROLES),
                inline=False
            )
            # Note: Avatar access might need message_content intent
            try:
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            except:
                pass  # Skip avatar if intent not available
            # Note: Member count might need members intent
            try:
                embed.set_footer(text=f"Member #{len(member.guild.members)}")
            except:
                embed.set_footer(text="Welcome to the server!")
            
            await welcome_channel.send(embed=embed)
        
        logger.info(f"New member joined: {member} ({member.id})")
        
        # Update member count channel
        await update_member_count_channel()
        
    except Exception as e:
        logger.error(f"Error in on_member_join: {e}")

@bot.event
async def on_member_remove(member):
    """Handle member leaving"""
    try:
        logger.info(f"Member left: {member} ({member.id})")
        
        # Update member count channel
        await update_member_count_channel()
        
    except Exception as e:
        logger.error(f"Error in on_member_remove: {e}")

@bot.event
async def on_message(message):
    """Handle message events"""
    if message.author.bot:
        return
    
    # Log all user messages to dedicated channel
    await log_user_message(message)
    
    # Update user activity
    try:
        db.update_user_activity(message.author.id, message.guild.id)
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")
    
    # Check for restricted channels
    if message.channel.name in RESTRICTED_CHANNELS:
        allowed_roles = RESTRICTED_CHANNELS[message.channel.name]
        user_roles = [role.name for role in message.author.roles]
        
        if not any(role in user_roles for role in allowed_roles):
            await message.delete()
            await message.author.send(f"You don't have permission to post in #{message.channel.name}")
            return
    
    # Auto-respond to !help
    if message.content.lower() == '!help':
        await send_help_message(message.channel, message.author)
        return
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    """Log deleted messages"""
    if message.author.bot:
        return
    
    global message_log_channel
    if not message_log_channel:
        return
    
    try:
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=f"{message.author.display_name} ({message.author})",
            icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
        )
        
        content = message.content if message.content else "*[No text content]*"
        if len(content) > 1024:
            content = content[:1021] + "..."
        embed.add_field(name="Deleted Message", value=content, inline=False)
        
        embed.add_field(name="Channel", value=f"#{message.channel.name}", inline=True)
        embed.add_field(name="User ID", value=str(message.author.id), inline=True)
        embed.add_field(name="Message ID", value=str(message.id), inline=True)
        
        if message.attachments:
            attachment_info = []
            for attachment in message.attachments:
                attachment_info.append(f"{attachment.filename} ({attachment.url})")
            embed.add_field(name="Attachments", value="\n".join(attachment_info[:3]), inline=False)
        
        embed.set_footer(text=f"Guild: {message.guild.name}")
        await message_log_channel.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error logging deleted message: {e}")

@bot.event
async def on_message_edit(before, after):
    """Log edited messages"""
    if before.author.bot or before.content == after.content:
        return
    
    global message_log_channel
    if not message_log_channel:
        return
    
    try:
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=f"{after.author.display_name} ({after.author})",
            icon_url=after.author.avatar.url if after.author.avatar else after.author.default_avatar.url
        )
        
        # Before content
        before_content = before.content if before.content else "*[No text content]*"
        if len(before_content) > 512:
            before_content = before_content[:509] + "..."
        embed.add_field(name="Before", value=before_content, inline=False)
        
        # After content
        after_content = after.content if after.content else "*[No text content]*"
        if len(after_content) > 512:
            after_content = after_content[:509] + "..."
        embed.add_field(name="After", value=after_content, inline=False)
        
        embed.add_field(name="Channel", value=f"#{after.channel.name}", inline=True)
        embed.add_field(name="User ID", value=str(after.author.id), inline=True)
        embed.add_field(name="Message ID", value=str(after.id), inline=True)
        
        embed.set_footer(text=f"Guild: {after.guild.name}")
        await message_log_channel.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error logging edited message: {e}")

async def send_help_message(channel, user=None):
    """Send help message with commands based on user permissions"""
    # Check if user has admin permissions
    user_is_admin = is_user_admin(user)
    
    embed = discord.Embed(
        title="Bot Commands Help 📚",
        description="Here are the available commands:",
        color=discord.Color.blue()
    )
    
    # Role Management
    embed.add_field(
        name="🎭 Role Management",
        value="`!role <role_name>` - Request a role\n`!myroles` - View your current roles",
        inline=False
    )
    
    # Admin Commands (only show if user is admin)
    if user_is_admin:
        embed.add_field(
            name="🛡️ Admin Commands",
            value="`!kick <user> [reason]` - Kick a member\n`!ban <user> [reason]` - Ban a member\n`!unban <user_id>` - Unban a member\n`!mute <user> [time] [reason]` - Mute a member\n`!unmute <user>` - Unmute a member\n`!purge <amount>` - Delete messages\n`!syncusers` - Sync all server members to database\n`!testlog` - Test Discord logging\n`!testmessagelog` - Test message logging",
            inline=False
        )
    
    # Dev Commands
    embed.add_field(
        name="💻 Dev Commands",
        value="`!fixmybug <description>` - Submit a bug report\n`!resources` - View shared resources",
        inline=False
    )
    
    # General
    embed.add_field(
        name="ℹ️ General",
        value="`!help` - Show this help message\n`!ping` - Check bot latency",
        inline=False
    )
    
    embed.add_field(
        name="Available Roles",
        value=", ".join(AVAILABLE_ROLES),
        inline=False
    )
    
    # Add footer based on admin status
    if user_is_admin:
        embed.set_footer(text="👑 Admin privileges active • Use commands responsibly!")
    else:
        embed.set_footer(text="💡 Tip: Get admin role to see additional commands!")
    
    await channel.send(embed=embed)

# Role Management Commands
@bot.command(name='role')
async def request_role(ctx, *, role_name: str = None):
    """Request a role"""
    if not role_name:
        await ctx.send("Please specify a role name. Available roles: " + ", ".join(AVAILABLE_ROLES))
        return
    
    # Check if role exists in available roles
    if role_name not in AVAILABLE_ROLES:
        await ctx.send(f"Role '{role_name}' is not available. Available roles: {', '.join(AVAILABLE_ROLES)}")
        return
    
    # Check if user already has the role
    user_roles = [role.name for role in ctx.author.roles]
    if role_name in user_roles:
        await ctx.send(f"You already have the '{role_name}' role!")
        return
    
    # Find the role in the guild
    guild_role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not guild_role:
        await ctx.send(f"Role '{role_name}' doesn't exist on this server. Please contact an admin.")
        return
    
    try:
        # Assign the role
        await ctx.author.add_roles(guild_role)
        
        # Store in database
        db.store_role_request(
            user_id=ctx.author.id,
            username=str(ctx.author),
            role_name=role_name,
            guild_id=ctx.guild.id,
            status='approved'
        )
        
        # Update user roles in database
        updated_roles = user_roles + [role_name]
        db.update_user_roles(ctx.author.id, ctx.guild.id, updated_roles)
        
        embed = discord.Embed(
            title="Role Assigned! ✅",
            description=f"You have been given the **{role_name}** role!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
        logger.info(f"Role '{role_name}' assigned to {ctx.author} ({ctx.author.id})")
        
    except discord.Forbidden:
        await ctx.send("I don't have permission to assign roles. Please contact an admin.")
    except Exception as e:
        logger.error(f"Error assigning role: {e}")
        await ctx.send("An error occurred while assigning the role.")

@bot.command(name='myroles')
async def my_roles(ctx):
    """Show user's current roles"""
    user_roles = [role.name for role in ctx.author.roles if role.name != '@everyone']
    
    if not user_roles:
        await ctx.send("You don't have any special roles.")
        return
    
    embed = discord.Embed(
        title=f"{ctx.author.display_name}'s Roles",
        description=", ".join(user_roles),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# Admin Commands
def is_user_admin(user):
    """Check if a user has admin permissions"""
    if not user or not hasattr(user, 'roles'):
        return False
    user_roles = [role.name for role in user.roles]
    return any(role in ADMIN_ROLES for role in user_roles) or user.guild_permissions.administrator

def is_admin():
    """Check if user has admin permissions (decorator)"""
    def predicate(ctx):
        return is_user_admin(ctx.author)
    return commands.check(predicate)

@bot.command(name='kick')
@is_admin()
async def kick_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member"""
    try:
        await member.kick(reason=reason)
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='kick',
            target_id=member.id,
            target_username=str(member),
            reason=reason,
            guild_id=ctx.guild.id
        )
        
        embed = discord.Embed(
            title="Member Kicked",
            description=f"**{member}** has been kicked.\n**Reason:** {reason}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        
        logger.info(f"{ctx.author} kicked {member} for: {reason}")
        
    except discord.Forbidden:
        await ctx.send("I don't have permission to kick this member.")
    except Exception as e:
        logger.error(f"Error kicking member: {e}")
        await ctx.send("An error occurred while kicking the member.")

@bot.command(name='ban')
@is_admin()
async def ban_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member"""
    try:
        await member.ban(reason=reason)
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='ban',
            target_id=member.id,
            target_username=str(member),
            reason=reason,
            guild_id=ctx.guild.id
        )
        
        embed = discord.Embed(
            title="Member Banned",
            description=f"**{member}** has been banned.\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
        logger.info(f"{ctx.author} banned {member} for: {reason}")
        
    except discord.Forbidden:
        await ctx.send("I don't have permission to ban this member.")
    except Exception as e:
        logger.error(f"Error banning member: {e}")
        await ctx.send("An error occurred while banning the member.")

@bot.command(name='unban')
@is_admin()
async def unban_member(ctx, user_id: int):
    """Unban a member by ID"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='unban',
            target_id=user_id,
            target_username=str(user),
            guild_id=ctx.guild.id
        )
        
        embed = discord.Embed(
            title="Member Unbanned",
            description=f"**{user}** has been unbanned.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
        logger.info(f"{ctx.author} unbanned {user}")
        
    except discord.NotFound:
        await ctx.send("User not found or not banned.")
    except Exception as e:
        logger.error(f"Error unbanning member: {e}")
        await ctx.send("An error occurred while unbanning the member.")

@bot.command(name='mute')
@is_admin()
async def mute_member(ctx, member: discord.Member, time: str = "10m", *, reason: str = "No reason provided"):
    """Mute a member"""
    try:
        # Parse time (simple implementation)
        duration = parse_time(time)
        
        # Create or get muted role
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False, speak=False))
            
            # Set permissions for all channels
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False)
        
        await member.add_roles(muted_role, reason=reason)
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='mute',
            target_id=member.id,
            target_username=str(member),
            reason=f"{reason} (Duration: {time})",
            guild_id=ctx.guild.id
        )
        
        embed = discord.Embed(
            title="Member Muted",
            description=f"**{member}** has been muted for **{time}**.\n**Reason:** {reason}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        
        # Auto-unmute after duration
        if duration:
            await asyncio.sleep(duration)
            try:
                await member.remove_roles(muted_role)
                await ctx.send(f"**{member}** has been automatically unmuted.")
            except:
                pass
        
        logger.info(f"{ctx.author} muted {member} for {time}: {reason}")
        
    except Exception as e:
        logger.error(f"Error muting member: {e}")
        await ctx.send("An error occurred while muting the member.")

@bot.command(name='unmute')
@is_admin()
async def unmute_member(ctx, member: discord.Member):
    """Unmute a member"""
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)
            
            # Log the action
            db.log_admin_action(
                admin_id=ctx.author.id,
                admin_username=str(ctx.author),
                action='unmute',
                target_id=member.id,
                target_username=str(member),
                guild_id=ctx.guild.id
            )
            
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"**{member}** has been unmuted.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
            logger.info(f"{ctx.author} unmuted {member}")
        else:
            await ctx.send("This member is not muted.")
            
    except Exception as e:
        logger.error(f"Error unmuting member: {e}")
        await ctx.send("An error occurred while unmuting the member.")

@bot.command(name='purge')
@is_admin()
async def purge_messages(ctx, amount: int):
    """Delete multiple messages"""
    if amount < 1 or amount > 100:
        await ctx.send("Please specify a number between 1 and 100.")
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='purge',
            reason=f"Deleted {len(deleted)-1} messages in #{ctx.channel.name}",
            guild_id=ctx.guild.id
        )
        
        embed = discord.Embed(
            title="Messages Purged",
            description=f"Deleted **{len(deleted)-1}** messages.",
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=embed)
        
        # Delete confirmation message after 5 seconds
        await asyncio.sleep(5)
        await msg.delete()
        
        logger.info(f"{ctx.author} purged {len(deleted)-1} messages in #{ctx.channel.name}")
        
    except Exception as e:
        logger.error(f"Error purging messages: {e}")
        await ctx.send("An error occurred while purging messages.")

# Dev Section Commands
@bot.command(name='fixmybug')
async def submit_bug(ctx, *, description: str = None):
    """Submit a bug report"""
    if not description:
        await ctx.send("Please provide a bug description. Usage: `!fixmybug <description>`")
        return
    
    try:
        # Store bug report
        result = db.store_bug_report(
            user_id=ctx.author.id,
            username=str(ctx.author),
            bug_description=description,
            guild_id=ctx.guild.id
        )
        
        # Send to bug channel
        bug_channel = discord.utils.get(ctx.guild.channels, name=BUG_CHANNEL)
        if bug_channel:
            embed = discord.Embed(
                title="🐛 New Bug Report",
                description=description,
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reported by", value=ctx.author.mention, inline=True)
            embed.add_field(name="Bug ID", value=str(result.inserted_id), inline=True)
            embed.set_footer(text=f"Report ID: {result.inserted_id}")
            
            await bug_channel.send(embed=embed)
        
        # Confirm to user
        embed = discord.Embed(
            title="Bug Report Submitted ✅",
            description=f"Your bug report has been submitted and posted to #{BUG_CHANNEL}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Report ID", value=str(result.inserted_id), inline=False)
        await ctx.send(embed=embed)
        
        logger.info(f"Bug report submitted by {ctx.author}: {description[:50]}...")
        
    except Exception as e:
        logger.error(f"Error submitting bug report: {e}")
        await ctx.send("An error occurred while submitting your bug report.")

@bot.command(name='resources')
async def show_resources(ctx):
    """Show recent resources"""
    try:
        resources = db.get_resources(limit=5)
        
        if not resources:
            await ctx.send("No resources found.")
            return
        
        embed = discord.Embed(
            title="📚 Recent Resources",
            color=discord.Color.blue()
        )
        
        for resource in resources:
            embed.add_field(
                name=resource['title'],
                value=f"{resource['content'][:100]}{'...' if len(resource['content']) > 100 else ''}\n*Shared by {resource['username']}*",
                inline=False
            )
        
        embed.set_footer(text=f"Showing {len(resources)} most recent resources")
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error fetching resources: {e}")
        await ctx.send("An error occurred while fetching resources.")

# Utility Commands
@bot.command(name='help')
async def help_command(ctx):
    """Show help message with role-based commands"""
    await send_help_message(ctx.channel, ctx.author)
    logger.info(f"Help command used by {ctx.author} ({ctx.author.id})")

@bot.command(name='ping')
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    
    # Test Discord logging
    logger.info(f"Ping command used by {ctx.author} ({ctx.author.id}) - Latency: {latency}ms")

@bot.command(name='testlog')
@is_admin()
async def test_logging(ctx):
    """Test Discord logging functionality (Admin only)"""
    logger.info("Testing INFO level logging to Discord")
    logger.warning("Testing WARNING level logging to Discord")
    logger.error("Testing ERROR level logging to Discord")
    
    await ctx.send("✅ Test logs sent! Check the #bot-logs channel in Admin category.")

@bot.command(name='testmessagelog')
@is_admin()
async def test_message_logging(ctx):
    """Test message logging functionality (Admin only)"""
    global message_log_channel
    
    if not message_log_channel:
        await ctx.send("❌ Message logging channel not set up yet.")
        return
    
    # Send test messages to demonstrate logging
    await ctx.send("🧪 Testing message logging...")
    await asyncio.sleep(1)
    await ctx.send("This message should be logged to #all-message-logs")
    await asyncio.sleep(1)
    
    # Edit the message to test edit logging
    msg = await ctx.send("This message will be edited...")
    await asyncio.sleep(2)
    await msg.edit(content="This message was edited! (Edit should be logged)")
    
    await ctx.send(f"✅ Message logging test complete! Check #{MESSAGE_LOG_CHANNEL} in Admin category.")

@bot.command(name='syncusers')
@is_admin()
async def sync_users(ctx):
    """Sync all guild members to database (Admin only)"""
    try:
        # Send initial message
        embed = discord.Embed(
            title="🔄 Syncing Users",
            description="Starting user synchronization process...",
            color=discord.Color.blue()
        )
        status_msg = await ctx.send(embed=embed)
        
        guild = ctx.guild
        if not guild:
            await ctx.send("❌ This command can only be used in a server.")
            return
        
        # Get users already in database
        existing_users = set(db.get_users_in_database(guild.id))
        logger.info(f"Found {len(existing_users)} existing users in database")
        
        # Get all guild members
        all_members = guild.members
        total_members = len(all_members)
        
        # Find users not in database
        new_users = []
        for member in all_members:
            if member.id not in existing_users:
                new_users.append(member)
        
        new_user_count = len(new_users)
        
        # Update status
        embed = discord.Embed(
            title="🔄 Syncing Users",
            description=f"Found **{new_user_count}** new users to sync out of **{total_members}** total members.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Status", value="Processing users...", inline=False)
        await status_msg.edit(embed=embed)
        
        # Sync new users
        synced_count = 0
        errors = 0
        
        for i, member in enumerate(new_users):
            try:
                # Extract user information
                user_data = await extract_user_data(member)
                
                # Store in database
                db.store_user_profile(
                    user_id=member.id,
                    username=str(member),
                    guild_id=guild.id,
                    display_name=member.display_name,
                    avatar_url=user_data['avatar_url'],
                    banner_url=user_data['banner_url'],
                    accent_color=user_data['accent_color'],
                    created_at=member.created_at,
                    joined_at=member.joined_at,
                    premium_since=member.premium_since,
                    nick=member.nick,
                    roles=[role.name for role in member.roles if role.name != '@everyone'],
                    status=str(member.status) if hasattr(member, 'status') else None,
                    activity=user_data['activity'],
                    is_bot=member.bot,
                    is_system=member.system
                )
                
                synced_count += 1
                
                # Update status every 10 users or on last user
                if (i + 1) % 10 == 0 or i == len(new_users) - 1:
                    progress_percent = int(((i + 1) / len(new_users)) * 100)
                    embed.description = f"Found **{new_user_count}** new users to sync out of **{total_members}** total members."
                    embed.set_field_at(0, name="Status", value=f"Processing users... {progress_percent}% ({i + 1}/{len(new_users)})", inline=False)
                    await status_msg.edit(embed=embed)
                
                # Small delay to avoid rate limits
                if i % 5 == 0:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error syncing user {member} ({member.id}): {e}")
                errors += 1
        
        # Final status
        embed = discord.Embed(
            title="✅ User Sync Complete",
            description=f"Synchronization completed successfully!",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Members", value=str(total_members), inline=True)
        embed.add_field(name="Already in DB", value=str(len(existing_users)), inline=True)
        embed.add_field(name="Newly Synced", value=str(synced_count), inline=True)
        
        if errors > 0:
            embed.add_field(name="Errors", value=str(errors), inline=True)
            embed.color = discord.Color.orange()
        
        embed.set_footer(text=f"Sync completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await status_msg.edit(embed=embed)
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='syncusers',
            reason=f"Synced {synced_count} new users to database",
            guild_id=guild.id
        )
        
        logger.info(f"{ctx.author} synced {synced_count} users to database (errors: {errors})")
        
    except Exception as e:
        logger.error(f"Error in sync_users command: {e}")
        embed = discord.Embed(
            title="❌ Sync Failed",
            description="An error occurred during user synchronization.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

async def extract_user_data(member):
    """Extract comprehensive user data from Discord member object"""
    try:
        # Get avatar URL
        avatar_url = None
        if member.avatar:
            avatar_url = member.avatar.url
        elif member.default_avatar:
            avatar_url = member.default_avatar.url
        
        # Get banner URL (if available)
        banner_url = None
        if hasattr(member, 'banner') and member.banner:
            banner_url = member.banner.url
        
        # Get accent color
        accent_color = None
        if hasattr(member, 'accent_color') and member.accent_color:
            accent_color = str(member.accent_color)
        elif hasattr(member, 'color') and member.color:
            accent_color = str(member.color)
        
        # Get activity information
        activity = None
        if hasattr(member, 'activity') and member.activity:
            activity = {
                'type': str(member.activity.type) if member.activity.type else None,
                'name': member.activity.name if hasattr(member.activity, 'name') else None,
                'details': member.activity.details if hasattr(member.activity, 'details') else None,
                'state': member.activity.state if hasattr(member.activity, 'state') else None
            }
        elif hasattr(member, 'activities') and member.activities:
            # Take the first activity if multiple
            first_activity = member.activities[0]
            activity = {
                'type': str(first_activity.type) if first_activity.type else None,
                'name': first_activity.name if hasattr(first_activity, 'name') else None,
                'details': first_activity.details if hasattr(first_activity, 'details') else None,
                'state': first_activity.state if hasattr(first_activity, 'state') else None
            }
        
        return {
            'avatar_url': avatar_url,
            'banner_url': banner_url,
            'accent_color': accent_color,
            'activity': activity
        }
        
    except Exception as e:
        logger.error(f"Error extracting user data for {member}: {e}")
        return {
            'avatar_url': None,
            'banner_url': None,
            'accent_color': None,
            'activity': None
        }

def parse_time(time_str):
    """Parse time string to seconds"""
    try:
        if time_str.endswith('s'):
            return int(time_str[:-1])
        elif time_str.endswith('m'):
            return int(time_str[:-1]) * 60
        elif time_str.endswith('h'):
            return int(time_str[:-1]) * 3600
        elif time_str.endswith('d'):
            return int(time_str[:-1]) * 86400
        else:
            return int(time_str) * 60  # Default to minutes
    except:
        return 600  # Default 10 minutes

# Error Handling
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided. Use `!help` for command usage.")
    else:
        logger.error(f"Unhandled error: {error}")
        await ctx.send("An unexpected error occurred.")

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        sys.exit(1)
    
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)
