import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
GUILD_ID = int(os.getenv('GUILD_ID', '0'))

# Channel Configuration
WELCOME_CHANNEL = os.getenv('WELCOME_CHANNEL', 'welcome')
BUG_CHANNEL = os.getenv('BUG_CHANNEL', 'fix-my-bug')
RESOURCES_CHANNEL = os.getenv('RESOURCES_CHANNEL', 'resources')
RULES_CHANNEL = os.getenv('RULES_CHANNEL', 'rules')
LOG_CHANNEL = os.getenv('LOG_CHANNEL', 'bot-logs')
MESSAGE_LOG_CHANNEL = os.getenv('MESSAGE_LOG_CHANNEL', 'all-message-logs')
MEMBER_COUNT_CHANNEL = os.getenv('MEMBER_COUNT_CHANNEL', 'members')
LEVELUP_CHANNEL = os.getenv('LEVELUP_CHANNEL', 'level-ups')

# Bot Settings
COMMAND_PREFIX = '!'
BOT_PERMISSIONS = 8  # Administrator permissions

# Available roles that users can request
AVAILABLE_ROLES = [
    'devGuy',
    'sysAdmin',
    'h@xor',
    'btw-i-use-arch'
]

# Restricted channels where only specific roles can post
RESTRICTED_CHANNELS = {
    'rules': ['Admin', 'Moderator']
}

# Admin roles
ADMIN_ROLES = ['Admin', 'Moderator']

# Logging configuration
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', 'INFO')
ADMIN_CATEGORY = os.getenv('ADMIN_CATEGORY', 'Admin')
GENERAL_CATEGORY = os.getenv('GENERAL_CATEGORY', 'General')
LEVEL_CATEGORY = os.getenv('LEVEL_CATEGORY', 'Level')

# Discord logging settings
ENABLE_DISCORD_LOGGING = os.getenv('ENABLE_DISCORD_LOGGING', 'true').lower() == 'true'
LOG_LEVELS_TO_DISCORD = ['ERROR', 'WARNING', 'INFO']  # Log levels to send to Discord

# Leveling System Configuration
XP_PER_MESSAGE = int(os.getenv('XP_PER_MESSAGE', '15'))  # Base XP per message
XP_BONUS_MIN = int(os.getenv('XP_BONUS_MIN', '5'))      # Minimum bonus XP
XP_BONUS_MAX = int(os.getenv('XP_BONUS_MAX', '25'))     # Maximum bonus XP
XP_COOLDOWN = int(os.getenv('XP_COOLDOWN', '0'))       # Cooldown between XP gains (seconds)
LEVEL_UP_BASE = int(os.getenv('LEVEL_UP_BASE', '100'))  # Base XP needed for level 1
LEVEL_UP_MULTIPLIER = float(os.getenv('LEVEL_UP_MULTIPLIER', '1.5'))  # XP multiplier per level
