# Discord Bot with MongoDB Integration 🤖  

A comprehensive Discord bot built with Python and discord.py, featuring role management, admin utilities, welcome system, and MongoDB data storage. The bot runs in Docker containers for easy deployment and scalability.

## 🚀 Features

### 🎭 Role Management
- **Role Requests**: Users can request available roles using `!role <role_name>`
- **Available Roles**: `devGuy`, `sysAdmin`, `h@xor`, `btw-i-use-arch`
- **Role Tracking**: All role assignments are stored in MongoDB
- **View Roles**: Users can check their current roles with `!myroles`

### 🛡️ Admin Utilities
- **Moderation**: Kick, ban, mute/unmute members
- **Message Management**: Bulk delete messages with `!purge`
- **Admin Logging**: All admin actions are logged to MongoDB
- **Permission System**: Only admins and moderators can use admin commands

### 👋 Welcome System
- **Auto Welcome**: Greets new members in the welcome channel
- **User Tracking**: Stores join date, roles, and activity in MongoDB
- **Customizable**: Beautiful embed messages with server information

### 📺 Channel Utilities
- **Channel Restrictions**: Prevent posting in specific channels (e.g., #rules)
- **Auto Help**: Responds to `!help` with comprehensive command list
- **Activity Tracking**: Updates user activity automatically

### 💻 Dev Section
- **Bug Reports**: `!fixmybug` command for submitting bug reports
- **Resource Sharing**: `!resources` command to view shared resources
- **Database Storage**: All reports and resources stored in MongoDB

### 🔒 Security Features
- **Member-Only**: Bot only responds to server members
- **Environment Variables**: Secure handling of sensitive data
- **Role-Based Permissions**: Admin commands restricted to authorized users
- **Input Validation**: Proper validation and error handling

## 📋 Prerequisites

- Docker and Docker Compose
- Discord Bot Token
- Discord Server with Administrator permissions

## 🛠️ Setup Instructions

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd eof-bot
```

### 2. Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Copy the bot token
4. Invite bot to your server with Administrator permissions
   - Use this URL: `https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot`

### 3. Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your configuration
nano .env
```

**Required Environment Variables:**
```env
BOT_TOKEN=your_discord_bot_token_here
GUILD_ID=your_discord_server_id_here
MONGO_ROOT_PASSWORD=your_secure_password_here
```

### 4. Create Required Discord Channels
Create these channels in your Discord server:
- `#welcome` - For welcome messages
- `#fix-my-bug` - For bug reports
- `#resources` - For shared resources
- `#rules` - Restricted channel

### 5. Create Required Roles
Create these roles in your Discord server:
- `Admin` - For administrators
- `Moderator` - For moderators
- `devGuy` - Available for users
- `sysAdmin` - Available for users
- `h@xor` - Available for users
- `btw-i-use-arch` - Available for users

### 6. Deploy with Docker

#### Start the Bot and Database:
```bash
# Start bot and MongoDB
docker-compose up -d

# View logs
docker-compose logs -f discord-bot

# Stop services
docker-compose down
```

#### Optional: Start with Database Management UI:
```bash
# Start with MongoDB Express for database management
docker-compose --profile tools up -d

# Access MongoDB Express at http://localhost:8081
# Username: admin, Password: admin123 (or your configured values)
```

### 7. Verify Installation
1. Check bot status in Discord (should show as online)
2. Test with `!ping` command
3. Try `!help` to see all available commands
4. Check MongoDB connection in logs

## 📚 Commands Reference

### General Commands
- `!help` - Show all available commands
- `!ping` - Check bot latency

### Role Management
- `!role <role_name>` - Request a role
- `!myroles` - View your current roles

### Admin Commands (Admin/Moderator only)
- `!kick <user> [reason]` - Kick a member
- `!ban <user> [reason]` - Ban a member
- `!unban <user_id>` - Unban a member by ID
- `!mute <user> [time] [reason]` - Mute a member (default: 10m)
- `!unmute <user>` - Unmute a member
- `!purge <amount>` - Delete messages (1-100)

### Dev Commands
- `!fixmybug <description>` - Submit a bug report
- `!resources` - View shared resources

## 🗄️ Database Structure

### Collections:
- **role_requests**: User role requests and assignments
- **admin_logs**: All administrative actions
- **users**: User data and activity tracking
- **bug_reports**: Bug reports from users
- **resources**: Shared resources and links

### Indexes:
Optimized indexes are automatically created for:
- User and guild lookups
- Timestamp-based queries
- Status filtering
- Text search on resources

## 🐳 Docker Architecture

### Services:
- **discord-bot**: Main bot application
- **mongodb**: Database server
- **mongo-express**: Database management UI (optional)

### Volumes:
- **mongodb_data**: Persistent database storage
- **logs**: Bot logs directory

### Networks:
- **bot-network**: Internal communication between services

## 🔧 Configuration

### Available Roles
Edit `bot/config.py` to modify available roles:
```python
AVAILABLE_ROLES = [
    'devGuy',
    'sysAdmin',
    'h@xor',
    'btw-i-use-arch'
]
```

### Channel Restrictions
Configure restricted channels:
```python
RESTRICTED_CHANNELS = {
    'rules': ['Admin', 'Moderator']
}
```

### Admin Roles
Set admin roles:
```python
ADMIN_ROLES = ['Admin', 'Moderator']
```

## 📊 Monitoring and Logs

### View Logs:
```bash
# Real-time logs
docker-compose logs -f discord-bot

# MongoDB logs
docker-compose logs -f mongodb

# All services
docker-compose logs -f
```

### Health Checks:
Both services include health checks for monitoring:
- Bot health check validates Python runtime
- MongoDB health check uses ping command

## 🛠️ Development

### Local Development:
```bash
# Install dependencies
pip install -r requirements.txt

# Set up local MongoDB or use Docker
docker run -d -p 27017:27017 --name mongo mongo:7.0

# Run bot locally
cd bot
python main.py
```

### Adding New Features:
1. Add new commands to `bot/main.py`
2. Update database methods in `bot/database.py`
3. Modify configuration in `bot/config.py`
4. Test thoroughly before deployment

## 🔒 Security Best Practices

1. **Never commit sensitive data**:
   - Keep `.env` file local only
   - Use strong passwords
   - Rotate credentials regularly

2. **Bot Permissions**:
   - Only grant necessary permissions
   - Regularly audit bot access
   - Monitor admin actions

3. **Database Security**:
   - Use authentication
   - Limit network access
   - Regular backups

4. **Code Security**:
   - Validate all inputs
   - Handle errors gracefully
   - Log security events

## 🚨 Troubleshooting

### Common Issues:

**Bot not responding:**
- Check bot token in `.env`
- Verify bot has necessary permissions
- Check Docker container logs

**Database connection failed:**
- Verify MongoDB is running
- Check connection string
- Ensure network connectivity

**Commands not working:**
- Verify user has required roles
- Check channel restrictions
- Review command syntax

**Permission errors:**
- Ensure bot has Administrator permissions
- Check role hierarchy in Discord
- Verify bot can access channels

### Debug Commands:
```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs --tail=100 discord-bot

# Access bot container
docker-compose exec discord-bot bash

# Access MongoDB
docker-compose exec mongodb mongosh
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [discord.py](https://discordpy.readthedocs.io/) - Discord API wrapper
- [MongoDB](https://www.mongodb.com/) - Database solution
- [Docker](https://www.docker.com/) - Containerization platform

## 📞 Support

For support and questions:
1. Check the troubleshooting section
2. Review Docker and bot logs
3. Open an issue on GitHub
4. Contact the development team

---

**Happy Discord Botting! 🎉**
