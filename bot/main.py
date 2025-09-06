import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, timedelta
import os
import sys
import random

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

# Global variables for leveling system
levelup_channel = None
user_cooldowns = {}  # Track XP gain cooldowns

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

async def setup_leveling_channel():
    """Set up the Level category and level-up channel"""
    global levelup_channel
    
    if not bot.guilds:
        return
        
    guild = bot.guilds[0]  # Use first guild
    
    # Find or create Level category
    level_category = discord.utils.get(guild.categories, name=LEVEL_CATEGORY)
    if not level_category:
        # Create Level category if it doesn't exist
        level_category = await guild.create_category(
            name=LEVEL_CATEGORY,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
        )
    
    # Find or create level-up channel
    levelup_channel = discord.utils.get(guild.channels, name=LEVELUP_CHANNEL)
    if not levelup_channel:
        levelup_channel = await guild.create_text_channel(
            name=LEVELUP_CHANNEL,
            category=level_category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )
        
        # Send welcome message to the channel
        embed = discord.Embed(
            title="🎉 Level Up Announcements",
            description=f"This channel will announce when members level up in **{guild.name}**!",
            color=discord.Color.gold()
        )
        embed.add_field(name="How it works", value="• Gain XP by sending messages\n• Level up when you reach XP thresholds\n• Get level roles automatically", inline=False)
        embed.set_footer(text=f"Level system activated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        await levelup_channel.send(embed=embed)
        
    logger.info(f"Level-up channel set up: #{levelup_channel.name}")

def calculate_level_from_xp(xp):
    """Calculate level based on XP using dynamic formula"""
    if xp < LEVEL_UP_BASE:
        return 1
    
    level = 1
    required_xp = LEVEL_UP_BASE
    
    while xp >= required_xp:
        level += 1
        required_xp = int(LEVEL_UP_BASE * (level ** LEVEL_UP_MULTIPLIER))
    
    return level - 1

def calculate_xp_for_level(level):
    """Calculate required XP for a specific level"""
    if level <= 1:
        return 0
    
    total_xp = 0
    for i in range(2, level + 1):
        total_xp += int(LEVEL_UP_BASE * (i ** LEVEL_UP_MULTIPLIER))
    
    return total_xp

def calculate_xp_to_next_level(current_xp, current_level):
    """Calculate XP needed to reach next level"""
    next_level_xp = calculate_xp_for_level(current_level + 1)
    return max(0, next_level_xp - current_xp)

def calculate_level_color(level):
    """Calculate progressively darker red color for level roles"""
    # Start with a light red and make it darker as level increases
    # Base red color: #FF4444 (bright red)
    # Target dark red: #800000 (dark red)
    
    # Clamp level to reasonable range for color calculation
    level = min(level, MAX_LEVEL_ROLES)
    
    # Calculate darkness factor (0.0 to 1.0)
    # Level 1 = lightest, higher levels = darker
    darkness_factor = min((level - 1) / 50.0, 1.0)  # Spread over 50 levels
    
    # RGB values for red progression
    # Start: #FF4444 (255, 68, 68)
    # End:   #800000 (128, 0, 0)
    start_r, start_g, start_b = 255, 68, 68
    end_r, end_g, end_b = 128, 0, 0
    
    # Interpolate between start and end colors
    r = int(start_r - (start_r - end_r) * darkness_factor)
    g = int(start_g - (start_g - end_g) * darkness_factor)
    b = int(start_b - (start_b - end_b) * darkness_factor)
    
    # Convert to hex color
    color_hex = (r << 16) | (g << 8) | b
    return color_hex

def calculate_message_length_xp(message_content):
    """Calculate bonus XP based on message length"""
    if not message_content:
        return 0
    
    message_length = len(message_content.strip())
    
    # Don't give XP for very short messages
    if message_length < MIN_MESSAGE_LENGTH:
        return 0
    
    # Calculate length bonus
    length_bonus = int(message_length * MESSAGE_LENGTH_MULTIPLIER)
    
    # Cap the bonus to prevent abuse
    length_bonus = min(length_bonus, MAX_LENGTH_BONUS)
    
    return length_bonus

async def get_or_create_level_role(guild, level):
    """Get or create a level role for the specified level"""
    if not ENABLE_LEVEL_ROLES or level > MAX_LEVEL_ROLES:
        return None
    
    # Calculate XP requirement for this level
    level_xp = calculate_xp_for_level(level)
    role_name = f"{LEVEL_ROLE_PREFIX} {level} (XP {level_xp:,})"
    
    # First try to find role with new format
    role = discord.utils.get(guild.roles, name=role_name)
    
    # If not found, try old format for backward compatibility
    if not role:
        old_role_name = f"{LEVEL_ROLE_PREFIX} {level}"
        old_role = discord.utils.get(guild.roles, name=old_role_name)
        
        if old_role:
            # Update old role to new format
            try:
                await old_role.edit(name=role_name, reason="Updated role name to include XP requirement")
                role = old_role
                logger.info(f"Updated role name from '{old_role_name}' to '{role_name}'")
            except Exception as e:
                logger.error(f"Failed to update role name for {old_role_name}: {e}")
                role = old_role  # Use old role if rename fails
    
    # Create new role if it doesn't exist
    if not role:
        try:
            # Calculate the red shade for this level
            level_color = calculate_level_color(level)
            
            # Create the role with the calculated red shade
            role = await guild.create_role(
                name=role_name,
                color=discord.Color(level_color),
                reason=f"Auto-created level role for level {level}"
            )
            logger.info(f"Created new level role: {role_name} with color #{level_color:06x}")
        except Exception as e:
            logger.error(f"Failed to create level role {role_name}: {e}")
            return None
    
    return role

async def update_user_level_role(member, old_level, new_level):
    """Update user's level role (remove old, add new)"""
    if not ENABLE_LEVEL_ROLES:
        return
    
    try:
        guild = member.guild
        
        # Remove old level role if it exists
        if old_level and old_level != new_level:
            # Try new format first
            old_level_xp = calculate_xp_for_level(old_level)
            new_format_name = f"{LEVEL_ROLE_PREFIX} {old_level} (XP {old_level_xp:,})"
            old_role = discord.utils.get(guild.roles, name=new_format_name)
            
            # If not found, try old format
            if not old_role:
                old_format_name = f"{LEVEL_ROLE_PREFIX} {old_level}"
                old_role = discord.utils.get(guild.roles, name=old_format_name)
            
            if old_role and old_role in member.roles:
                await member.remove_roles(old_role, reason=f"Level up from {old_level} to {new_level}")
                logger.debug(f"Removed {old_role.name} from {member}")
        
        # Add new level role
        new_role = await get_or_create_level_role(guild, new_level)
        if new_role and new_role not in member.roles:
            await member.add_roles(new_role, reason=f"Level up to {new_level}")
            logger.debug(f"Added {new_role.name} to {member}")
            
    except Exception as e:
        logger.error(f"Error updating level role for {member}: {e}")

async def announce_level_up(member, old_level, new_level, new_xp):
    """Announce level up in the level-up channel"""
    global levelup_channel
    
    if not levelup_channel:
        return
    
    try:
        # Create level up embed
        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"{member.mention} has reached **Level {new_level}**!",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=member.display_name,
            icon_url=member.avatar.url if member.avatar else member.default_avatar.url
        )
        
        embed.add_field(name="Previous Level", value=str(old_level), inline=True)
        embed.add_field(name="New Level", value=str(new_level), inline=True)
        embed.add_field(name="Total XP", value=f"{new_xp:,}", inline=True)
        
        # Calculate XP to next level
        xp_to_next = calculate_xp_to_next_level(new_xp, new_level)
        if xp_to_next > 0:
            embed.add_field(name="XP to Next Level", value=f"{xp_to_next:,}", inline=True)
        
        embed.set_footer(text=f"Keep chatting to earn more XP!")
        
        await levelup_channel.send(embed=embed)
        logger.info(f"Announced level up for {member} (Level {old_level} → {new_level})")
        
    except Exception as e:
        logger.error(f"Error announcing level up for {member}: {e}")

async def process_xp_gain(message):
    """Process XP gain for a message"""
    global user_cooldowns
    
    # Skip bots
    if message.author.bot:
        return
    
    user_id = message.author.id
    guild_id = message.guild.id
    current_time = datetime.utcnow()
    
    # Check cooldown
    cooldown_key = f"{user_id}_{guild_id}"
    if cooldown_key in user_cooldowns:
        time_diff = (current_time - user_cooldowns[cooldown_key]).total_seconds()
        if time_diff < XP_COOLDOWN:
            return  # Still in cooldown
    
    try:
        # Get current user data
        user_data = db.get_user_xp(user_id, guild_id)
        current_xp = user_data['xp']
        current_level = user_data['level']
        
        # Calculate XP gain (base + random bonus + message length bonus)
        base_xp = XP_PER_MESSAGE
        bonus_xp = random.randint(XP_BONUS_MIN, XP_BONUS_MAX)
        length_xp = calculate_message_length_xp(message.content)
        xp_gained = base_xp + bonus_xp + length_xp
        
        new_xp = current_xp + xp_gained
        new_level = calculate_level_from_xp(new_xp)
        
        # Update cooldown
        user_cooldowns[cooldown_key] = current_time
        
        # Update database
        db.update_user_xp(user_id, guild_id, xp_gained, new_level if new_level != current_level else None)
        
        # Check for level up
        if new_level > current_level:
            # Update role
            await update_user_level_role(message.author, current_level, new_level)
            
            # Announce level up
            await announce_level_up(message.author, current_level, new_level, new_xp)
            
            logger.info(f"{message.author} leveled up from {current_level} to {new_level} (XP: {new_xp})")
        
    except Exception as e:
        logger.error(f"Error processing XP gain for {message.author}: {e}")

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
    
    # Set up leveling system
    await setup_leveling_channel()
    
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
        
        # Assign Level 1 role to new member
        if ENABLE_LEVEL_ROLES:
            try:
                level_1_role = await get_or_create_level_role(member.guild, 1)
                if level_1_role and level_1_role not in member.roles:
                    await member.add_roles(level_1_role, reason="Auto-assigned Level 1 role to new member")
                    logger.info(f"Assigned Level 1 role to new member: {member}")
            except Exception as e:
                logger.error(f"Error assigning Level 1 role to new member {member}: {e}")
        
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
    
    # Process XP gain for leveling system
    await process_xp_gain(message)
    
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
            value="`!kick <user> [reason]` - Kick a member\n`!ban <user> [reason]` - Ban a member\n`!unban <user_id>` - Unban a member\n`!mute <user> [time] [reason]` - Mute a member\n`!unmute <user>` - Unmute a member\n`!purge <amount>` - Delete messages\n`!syncusers` - Sync all server members to database\n`!resetlevel <user>` - Reset user's level and XP\n`!setlevel <user> <level>` - Set user's level\n`!addxp <user> <amount>` - Add/remove XP points\n`!synclevelroles` - Sync level roles for users without them\n`!updateroles` - Update role names to include XP\n`!levelstats` - Show leveling system statistics\n`!testlog` - Test Discord logging\n`!testmessagelog` - Test message logging",
            inline=False
        )
    
    # Leveling Commands
    embed.add_field(
        name="📈 Leveling System",
        value="`!level [user]` - Check level and XP\n`!leaderboard [limit]` - Show server leaderboard\n`!rank [user]` - Alias for !level",
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

# Leveling System Commands
@bot.command(name='level', aliases=['rank'])
async def check_level(ctx, member: discord.Member = None):
    """Check your or someone else's level and XP"""
    target = member or ctx.author
    
    try:
        user_data = db.get_user_xp(target.id, ctx.guild.id)
        current_xp = user_data['xp']
        current_level = user_data['level']
        messages_count = user_data['messages_count']
        
        # Calculate XP for current and next level
        current_level_xp = calculate_xp_for_level(current_level)
        next_level_xp = calculate_xp_for_level(current_level + 1)
        xp_to_next = next_level_xp - current_xp
        xp_progress = current_xp - current_level_xp
        xp_needed = next_level_xp - current_level_xp
        
        # Get user's rank
        rank = db.get_user_rank(target.id, ctx.guild.id)
        
        embed = discord.Embed(
            title=f"📊 Level Statistics",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=target.display_name,
            icon_url=target.avatar.url if target.avatar else target.default_avatar.url
        )
        
        embed.add_field(name="Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="Rank", value=f"**#{rank}**" if rank else "Unranked", inline=True)
        embed.add_field(name="Total XP", value=f"{current_xp:,}", inline=True)
        
        embed.add_field(name="Messages Sent", value=f"{messages_count:,}", inline=True)
        embed.add_field(name="XP to Next Level", value=f"{xp_to_next:,}", inline=True)
        
        # Progress bar
        if xp_needed > 0:
            progress_percent = int((xp_progress / xp_needed) * 100)
            progress_bar = "█" * (progress_percent // 10) + "░" * (10 - (progress_percent // 10))
            embed.add_field(name="Progress to Next Level", value=f"`{progress_bar}` {progress_percent}%", inline=False)
        
        embed.set_footer(text=f"Keep chatting to earn more XP!")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error checking level for {target}: {e}")
        await ctx.send("An error occurred while checking level information.")

@bot.command(name='leaderboard', aliases=['lb', 'top'])
async def leaderboard(ctx, limit: int = 10):
    """Show the server leaderboard"""
    try:
        if limit < 1 or limit > 20:
            limit = 10
        
        leaderboard_data = db.get_leaderboard(ctx.guild.id, limit)
        
        if not leaderboard_data:
            await ctx.send("No users found in the leaderboard.")
            return
        
        embed = discord.Embed(
            title="🏆 Server Leaderboard",
            description=f"Top {len(leaderboard_data)} members by XP",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        leaderboard_text = ""
        for i, user_data in enumerate(leaderboard_data, 1):
            try:
                user = ctx.guild.get_member(user_data['user_id'])
                username = user.display_name if user else f"User {user_data['user_id']}"
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{username}** - Level {user_data['level']} ({user_data['xp']:,} XP)\n"
                
            except Exception as e:
                logger.error(f"Error processing leaderboard entry {i}: {e}")
                continue
        
        embed.description = leaderboard_text
        embed.set_footer(text=f"Guild: {ctx.guild.name}")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error showing leaderboard: {e}")
        await ctx.send("An error occurred while fetching the leaderboard.")

@bot.command(name='resetlevel')
@is_admin()
async def reset_user_level(ctx, member: discord.Member):
    """Reset a user's level and XP (Admin only)"""
    try:
        # Reset in database
        db.reset_user_xp(member.id, ctx.guild.id)
        
        # Remove all level roles (both old and new formats)
        if ENABLE_LEVEL_ROLES:
            level_roles = [
                role for role in member.roles 
                if role.name.startswith(LEVEL_ROLE_PREFIX) and (
                    role.name.startswith(f"{LEVEL_ROLE_PREFIX} ") and 
                    (role.name.count(" ") == 1 or "(XP " in role.name)
                )
            ]
            if level_roles:
                await member.remove_roles(*level_roles, reason=f"Level reset by {ctx.author}")
            
            # Add Level 1 role
            level_1_role = await get_or_create_level_role(ctx.guild, 1)
            if level_1_role and level_1_role not in member.roles:
                await member.add_roles(level_1_role, reason=f"Level reset by {ctx.author}")
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='resetlevel',
            target_id=member.id,
            target_username=str(member),
            guild_id=ctx.guild.id
        )
        
        embed = discord.Embed(
            title="✅ Level Reset",
            description=f"**{member.display_name}**'s level and XP have been reset to Level 1.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
        logger.info(f"{ctx.author} reset level for {member}")
        
    except Exception as e:
        logger.error(f"Error resetting level for {member}: {e}")
        await ctx.send("An error occurred while resetting the user's level.")

@bot.command(name='setlevel')
@is_admin()
async def set_user_level(ctx, member: discord.Member, level: int):
    """Set a user's level to a specific value (Admin only)"""
    try:
        # Validate level
        if level < 1:
            await ctx.send("❌ Level must be at least 1.")
            return
        
        if level > MAX_LEVEL_ROLES:
            await ctx.send(f"❌ Level cannot exceed {MAX_LEVEL_ROLES}.")
            return
        
        # Get current user data
        current_data = db.get_user_xp(member.id, ctx.guild.id)
        old_level = current_data['level']
        
        if level == old_level:
            await ctx.send(f"**{member.display_name}** is already at Level {level}.")
            return
        
        # Calculate required XP for the target level
        required_xp = calculate_xp_for_level(level)
        
        # Update database with new level and XP
        db.update_user_xp(
            user_id=member.id,
            guild_id=ctx.guild.id,
            xp_gained=required_xp - current_data['xp'],  # Adjust XP to match level
            new_level=level
        )
        
        # Update level roles
        if ENABLE_LEVEL_ROLES:
            # Remove old level role (try both formats)
            if old_level:
                # Try new format first
                old_level_xp = calculate_xp_for_level(old_level)
                new_format_name = f"{LEVEL_ROLE_PREFIX} {old_level} (XP {old_level_xp:,})"
                old_role = discord.utils.get(ctx.guild.roles, name=new_format_name)
                
                # If not found, try old format
                if not old_role:
                    old_format_name = f"{LEVEL_ROLE_PREFIX} {old_level}"
                    old_role = discord.utils.get(ctx.guild.roles, name=old_format_name)
                
                if old_role and old_role in member.roles:
                    await member.remove_roles(old_role, reason=f"Level changed by {ctx.author}")
            
            # Add new level role
            new_role = await get_or_create_level_role(ctx.guild, level)
            if new_role and new_role not in member.roles:
                await member.add_roles(new_role, reason=f"Level set to {level} by {ctx.author}")
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='setlevel',
            target_id=member.id,
            target_username=str(member),
            reason=f"Level changed from {old_level} to {level}",
            guild_id=ctx.guild.id
        )
        
        # Create response embed
        embed = discord.Embed(
            title="✅ Level Updated",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=member.display_name,
            icon_url=member.avatar.url if member.avatar else member.default_avatar.url
        )
        
        embed.add_field(name="Previous Level", value=str(old_level), inline=True)
        embed.add_field(name="New Level", value=str(level), inline=True)
        embed.add_field(name="New XP", value=f"{required_xp:,}", inline=True)
        
        # Calculate XP to next level
        if level < MAX_LEVEL_ROLES:
            xp_to_next = calculate_xp_to_next_level(required_xp, level)
            embed.add_field(name="XP to Next Level", value=f"{xp_to_next:,}", inline=True)
        
        embed.set_footer(text=f"Level set by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
        
        # Announce level change in level-up channel if it's an upgrade
        if level > old_level:
            await announce_level_up(member, old_level, level, required_xp)
        
        logger.info(f"{ctx.author} set {member}'s level from {old_level} to {level}")
        
    except ValueError:
        await ctx.send("❌ Please provide a valid level number.")
    except Exception as e:
        logger.error(f"Error setting level for {member}: {e}")
        await ctx.send("An error occurred while setting the user's level.")

@bot.command(name='addxp')
@is_admin()
async def add_user_xp(ctx, member: discord.Member, xp_amount: int):
    """Add XP points to a specific user (Admin only)"""
    try:
        # Validate XP amount
        if xp_amount == 0:
            await ctx.send("❌ XP amount cannot be zero.")
            return
        
        if abs(xp_amount) > 10000:
            await ctx.send("❌ XP amount cannot exceed ±10,000 at once.")
            return
        
        # Get current user data
        current_data = db.get_user_xp(member.id, ctx.guild.id)
        old_xp = current_data['xp']
        old_level = current_data['level']
        
        # Calculate new XP (don't let it go below 0)
        new_xp = max(0, old_xp + xp_amount)
        new_level = calculate_level_from_xp(new_xp)
        
        # Update database
        db.update_user_xp(
            user_id=member.id,
            guild_id=ctx.guild.id,
            xp_gained=new_xp - old_xp,  # Actual XP change (might be different if capped at 0)
            new_level=new_level if new_level != old_level else None
        )
        
        # Handle level changes
        level_changed = new_level != old_level
        if level_changed and ENABLE_LEVEL_ROLES:
            await update_user_level_role(member, old_level, new_level)
        
        # Log the action
        action_type = 'addxp' if xp_amount > 0 else 'removexp'
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action=action_type,
            target_id=member.id,
            target_username=str(member),
            reason=f"{'Added' if xp_amount > 0 else 'Removed'} {abs(xp_amount)} XP",
            guild_id=ctx.guild.id
        )
        
        # Create response embed
        embed = discord.Embed(
            title="✅ XP Updated",
            color=discord.Color.green() if xp_amount > 0 else discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=member.display_name,
            icon_url=member.avatar.url if member.avatar else member.default_avatar.url
        )
        
        # Show XP change
        xp_change_text = f"+{xp_amount:,}" if xp_amount > 0 else f"{xp_amount:,}"
        embed.add_field(name="XP Change", value=xp_change_text, inline=True)
        embed.add_field(name="Previous XP", value=f"{old_xp:,}", inline=True)
        embed.add_field(name="New XP", value=f"{new_xp:,}", inline=True)
        
        # Show level information
        if level_changed:
            embed.add_field(name="Previous Level", value=str(old_level), inline=True)
            embed.add_field(name="New Level", value=str(new_level), inline=True)
            
            # Add level change indicator
            if new_level > old_level:
                embed.add_field(name="Level Change", value="📈 Level Up!", inline=True)
            else:
                embed.add_field(name="Level Change", value="📉 Level Down", inline=True)
        else:
            embed.add_field(name="Current Level", value=str(new_level), inline=True)
            
            # Show XP to next level
            if new_level < MAX_LEVEL_ROLES:
                xp_to_next = calculate_xp_to_next_level(new_xp, new_level)
                embed.add_field(name="XP to Next Level", value=f"{xp_to_next:,}", inline=True)
        
        embed.set_footer(text=f"XP adjusted by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
        
        # Announce level up if applicable
        if level_changed and new_level > old_level:
            await announce_level_up(member, old_level, new_level, new_xp)
        
        action_word = "added" if xp_amount > 0 else "removed"
        logger.info(f"{ctx.author} {action_word} {abs(xp_amount)} XP to {member} (Level {old_level}→{new_level})")
        
    except ValueError:
        await ctx.send("❌ Please provide a valid XP amount (number).")
    except Exception as e:
        logger.error(f"Error adding XP to {member}: {e}")
        await ctx.send("An error occurred while updating the user's XP.")

@bot.command(name='updateroles')
@is_admin()
async def update_role_names(ctx):
    """Update all level role names to include XP requirements (Admin only)"""
    try:
        # Send initial message
        embed = discord.Embed(
            title="🔄 Updating Role Names",
            description="Starting role name update process...",
            color=discord.Color.blue()
        )
        status_msg = await ctx.send(embed=embed)
        
        guild = ctx.guild
        
        # Find all old format level roles
        old_roles = []
        for role in guild.roles:
            if (role.name.startswith(f"{LEVEL_ROLE_PREFIX} ") and 
                role.name.count(" ") == 1 and 
                "(XP " not in role.name):
                
                # Extract level number
                try:
                    level_str = role.name.replace(f"{LEVEL_ROLE_PREFIX} ", "")
                    level = int(level_str)
                    old_roles.append((role, level))
                except ValueError:
                    continue
        
        total_roles = len(old_roles)
        
        # Update status
        embed = discord.Embed(
            title="🔄 Updating Role Names",
            description=f"Found **{total_roles}** roles to update.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Status", value="Updating role names...", inline=False)
        await status_msg.edit(embed=embed)
        
        if total_roles == 0:
            embed = discord.Embed(
                title="✅ Update Complete",
                description="All role names are already up to date!",
                color=discord.Color.green()
            )
            await status_msg.edit(embed=embed)
            return
        
        # Update roles
        updated_count = 0
        errors = 0
        
        for i, (role, level) in enumerate(old_roles):
            try:
                # Calculate new name
                level_xp = calculate_xp_for_level(level)
                new_name = f"{LEVEL_ROLE_PREFIX} {level} (XP {level_xp:,})"
                
                # Update role name
                await role.edit(name=new_name, reason="Updated role name to include XP requirement")
                updated_count += 1
                logger.info(f"Updated role name: {role.name} → {new_name}")
                
                # Update status every 5 roles
                if (i + 1) % 5 == 0 or i == len(old_roles) - 1:
                    progress_percent = int(((i + 1) / len(old_roles)) * 100)
                    embed.description = f"Found **{total_roles}** roles to update."
                    embed.set_field_at(0, name="Status", value=f"Updating role names... {progress_percent}% ({i + 1}/{len(old_roles)})", inline=False)
                    await status_msg.edit(embed=embed)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error updating role {role.name}: {e}")
                errors += 1
        
        # Final status
        embed = discord.Embed(
            title="✅ Role Names Updated",
            description=f"Role name update completed successfully!",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Roles Found", value=str(total_roles), inline=True)
        embed.add_field(name="Successfully Updated", value=str(updated_count), inline=True)
        
        if errors > 0:
            embed.add_field(name="Errors", value=str(errors), inline=True)
            embed.color = discord.Color.orange()
        
        embed.set_footer(text=f"Update completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await status_msg.edit(embed=embed)
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='updateroles',
            reason=f"Updated {updated_count} role names to include XP requirements",
            guild_id=guild.id
        )
        
        logger.info(f"{ctx.author} updated {updated_count} role names (errors: {errors})")
        
    except Exception as e:
        logger.error(f"Error in update_role_names command: {e}")
        embed = discord.Embed(
            title="❌ Update Failed",
            description="An error occurred during role name update.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='levelstats')
@is_admin()
async def level_stats(ctx):
    """Show leveling system statistics (Admin only)"""
    try:
        stats = db.get_level_stats(ctx.guild.id)
        
        if not stats:
            await ctx.send("No leveling statistics available.")
            return
        
        embed = discord.Embed(
            title="📈 Leveling System Statistics",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Total Users", value=f"{stats['total_users']:,}", inline=True)
        embed.add_field(name="Total XP Earned", value=f"{stats['total_xp']:,}", inline=True)
        embed.add_field(name="Total Messages", value=f"{stats['total_messages']:,}", inline=True)
        embed.add_field(name="Average Level", value=f"{stats['avg_level']:.1f}", inline=True)
        embed.add_field(name="Highest Level", value=f"{stats['max_level']}", inline=True)
        
        # System configuration
        config_text = f"""
        **XP per Message:** {XP_PER_MESSAGE} + {XP_BONUS_MIN}-{XP_BONUS_MAX} bonus
        **Message Length Bonus:** {MESSAGE_LENGTH_MULTIPLIER}x per char (max {MAX_LENGTH_BONUS})
        **Min Message Length:** {MIN_MESSAGE_LENGTH} characters
        **Cooldown:** {XP_COOLDOWN}s
        **Level Formula:** Base {LEVEL_UP_BASE} × Level^{LEVEL_UP_MULTIPLIER}
        **Level Roles:** {'Enabled (Red Gradient)' if ENABLE_LEVEL_ROLES else 'Disabled'}
        """
        embed.add_field(name="System Configuration", value=config_text, inline=False)
        
        embed.set_footer(text=f"Guild: {ctx.guild.name}")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error showing level stats: {e}")
        await ctx.send("An error occurred while fetching leveling statistics.")

@bot.command(name='synclevelroles')
@is_admin()
async def sync_level_roles(ctx):
    """Sync level roles for users who don't have them (Admin only)"""
    try:
        if not ENABLE_LEVEL_ROLES:
            await ctx.send("❌ Level roles are disabled in the configuration.")
            return
        
        # Send initial message
        embed = discord.Embed(
            title="🔄 Syncing Level Roles",
            description="Starting level role synchronization process...",
            color=discord.Color.blue()
        )
        status_msg = await ctx.send(embed=embed)
        
        guild = ctx.guild
        
        # Get all members and their level data
        all_members = guild.members
        members_without_roles = []
        total_members = len(all_members)
        
        # Check each member for level roles
        for member in all_members:
            if member.bot:
                continue  # Skip bots
            
            # Check if member has any level role (both old and new formats)
            has_level_role = any(
                role.name.startswith(LEVEL_ROLE_PREFIX) and (
                    role.name.startswith(f"{LEVEL_ROLE_PREFIX} ") and 
                    (role.name.count(" ") == 1 or "(XP " in role.name)  # Old format has 1 space, new format has "(XP "
                )
                for role in member.roles
            )
            
            if not has_level_role:
                # Get their level from database
                user_data = db.get_user_xp(member.id, guild.id)
                if user_data:
                    members_without_roles.append((member, user_data['level']))
        
        members_to_sync = len(members_without_roles)
        
        # Update status
        embed = discord.Embed(
            title="🔄 Syncing Level Roles",
            description=f"Found **{members_to_sync}** members without level roles out of **{total_members}** total members.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Status", value="Processing members...", inline=False)
        await status_msg.edit(embed=embed)
        
        if members_to_sync == 0:
            embed = discord.Embed(
                title="✅ Sync Complete",
                description="All members already have appropriate level roles!",
                color=discord.Color.green()
            )
            await status_msg.edit(embed=embed)
            return
        
        # Process members
        synced_count = 0
        errors = 0
        
        for i, (member, level) in enumerate(members_without_roles):
            try:
                # Get or create the appropriate level role
                level_role = await get_or_create_level_role(guild, level)
                
                if level_role and level_role not in member.roles:
                    await member.add_roles(level_role, reason=f"Level role sync by {ctx.author}")
                    synced_count += 1
                    logger.debug(f"Added {level_role.name} to {member}")
                
                # Update status every 10 members or on last member
                if (i + 1) % 10 == 0 or i == len(members_without_roles) - 1:
                    progress_percent = int(((i + 1) / len(members_without_roles)) * 100)
                    embed.description = f"Found **{members_to_sync}** members without level roles out of **{total_members}** total members."
                    embed.set_field_at(0, name="Status", value=f"Processing members... {progress_percent}% ({i + 1}/{len(members_without_roles)})", inline=False)
                    await status_msg.edit(embed=embed)
                
                # Small delay to avoid rate limits
                if i % 5 == 0:
                    await asyncio.sleep(0.2)
                    
            except Exception as e:
                logger.error(f"Error syncing level role for {member} (Level {level}): {e}")
                errors += 1
        
        # Final status
        embed = discord.Embed(
            title="✅ Level Role Sync Complete",
            description=f"Level role synchronization completed successfully!",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Members", value=str(total_members), inline=True)
        embed.add_field(name="Members Needing Roles", value=str(members_to_sync), inline=True)
        embed.add_field(name="Roles Assigned", value=str(synced_count), inline=True)
        
        if errors > 0:
            embed.add_field(name="Errors", value=str(errors), inline=True)
            embed.color = discord.Color.orange()
        
        embed.set_footer(text=f"Sync completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await status_msg.edit(embed=embed)
        
        # Log the action
        db.log_admin_action(
            admin_id=ctx.author.id,
            admin_username=str(ctx.author),
            action='synclevelroles',
            reason=f"Synced level roles for {synced_count} members",
            guild_id=guild.id
        )
        
        logger.info(f"{ctx.author} synced level roles for {synced_count} members (errors: {errors})")
        
    except Exception as e:
        logger.error(f"Error in sync_level_roles command: {e}")
        embed = discord.Embed(
            title="❌ Sync Failed",
            description="An error occurred during level role synchronization.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

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
