# 🤖 Discord Bot Invitation Instructions

## Your Bot Details:
- **Bot ID (Client ID)**: `1412836680033107990`
- **Guild ID**: `1410581385558622262`

## 🔗 Correct Bot Invitation URL

Use this URL to invite your bot to the Discord server:

```
https://discord.com/api/oauth2/authorize?client_id=1412836680033107990&permissions=8&scope=bot
```

## 🛠️ Alternative URLs with Different Permission Levels:

### Administrator Permissions (Recommended):
```
https://discord.com/api/oauth2/authorize?client_id=1412836680033107990&permissions=8&scope=bot
```

### Specific Permissions Only:
```
https://discord.com/api/oauth2/authorize?client_id=1412836680033107990&permissions=1644971949558&scope=bot
```

### With Application Commands (Slash Commands):
```
https://discord.com/api/oauth2/authorize?client_id=1412836680033107990&permissions=8&scope=bot%20applications.commands
```

## 🔧 How to Fix the "Integration requires code grant" Error:

### Method 1: Use the Correct URL (Recommended)
1. Click on the **Administrator Permissions** URL above
2. Select your Discord server from the dropdown
3. Click "Authorize"
4. Complete the CAPTCHA if prompted

### Method 2: Manual Setup in Discord Developer Portal
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application (ID: 1412836680033107990)
3. Go to **OAuth2** → **URL Generator**
4. Select scopes: `bot` (and optionally `applications.commands`)
5. Select permissions: `Administrator` or specific permissions
6. Copy the generated URL and use it

### Method 3: Fix OAuth Settings
1. In Discord Developer Portal → **OAuth2** → **General**
2. Add redirect URI: `https://discord.com/api/oauth2/authorize`
3. Save changes
4. Use the invitation URL again

## 🚨 Troubleshooting "Integration requires code grant":

**MOST COMMON FIX - Check Bot Settings:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your bot → **Bot** section
3. **TURN OFF** "Require OAuth2 Code Grant" (this is likely the issue!)
4. Save changes and try the invitation URL again

**Other Solutions:**
1. In **OAuth2 → General**, add redirect URI: `https://discord.com/api/oauth2/authorize`
2. Use **OAuth2 → URL Generator** to create a fresh invitation URL
3. Try these alternative URLs:
   - Basic: `https://discord.com/api/oauth2/authorize?client_id=1412836680033107990&scope=bot&permissions=0`
   - With perms: `https://discord.com/api/oauth2/authorize?client_id=1412836680033107990&scope=bot&permissions=1644971949558`

**If you still get the error:**
1. Make sure you're the server owner or have "Manage Server" permissions
2. Check that the bot isn't already in the server
3. Try removing the bot first, then re-inviting
4. Clear browser cache and try again

**If the bot appears offline after invitation:**
1. Make sure your Docker containers are running: `docker-compose ps`
2. Check bot logs: `docker-compose logs discord-bot`
3. Verify the BOT_TOKEN in your .env file is correct

## ✅ Verification Steps:

After successful invitation:
1. Bot should appear in your server's member list
2. Bot should show as "Online" (green status)
3. Test with `!ping` command
4. Try `!help` to see all commands

## 🔑 Required Permissions for Full Functionality:

- **Administrator** (simplest option)
- OR these specific permissions:
  - Manage Roles
  - Kick Members  
  - Ban Members
  - Manage Messages
  - Read Message History
  - Send Messages
  - Use External Emojis
  - Add Reactions
  - Manage Channels (for mute functionality)

---

**Note**: Keep your bot token secure and never share it publicly!
