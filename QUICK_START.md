# 🚀 Quick Start Guide

## 1. Get Your Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application → Bot → Copy token
3. Invite bot to server with Administrator permissions

## 2. Setup Environment
```bash
# Copy environment template
cp env.example .env

# Edit with your values
nano .env
```

**Required:**
- `BOT_TOKEN` - Your Discord bot token
- `GUILD_ID` - Your Discord server ID
- `MONGO_ROOT_PASSWORD` - Secure password for MongoDB

## 3. Create Discord Channels
- `#welcome` - Welcome messages
- `#fix-my-bug` - Bug reports  
- `#resources` - Shared resources
- `#rules` - Restricted channel

## 4. Create Discord Roles
- `Admin` - Bot administrators
- `Moderator` - Bot moderators
- `devGuy` - User role
- `sysAdmin` - User role
- `h@xor` - User role
- `btw-i-use-arch` - User role

## 5. Start the Bot
```bash
# Run setup (one time)
./scripts/setup.sh

# Start bot
./scripts/start.sh

# View logs
docker-compose logs -f discord-bot
```

## 6. Test Commands
- `!help` - Show all commands
- `!ping` - Test bot response
- `!role devGuy` - Request a role

## 🎉 You're Ready!

Your Discord bot is now running with:
- ✅ Role management system
- ✅ Admin utilities (kick, ban, mute, purge)
- ✅ Welcome system
- ✅ Bug reporting
- ✅ MongoDB data storage
- ✅ Docker containerization

For detailed documentation, see `README.md`
