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

# Discord logging settings
ENABLE_DISCORD_LOGGING = os.getenv('ENABLE_DISCORD_LOGGING', 'true').lower() == 'true'
LOG_LEVELS_TO_DISCORD = ['ERROR', 'WARNING', 'INFO']  # Log levels to send to Discord
