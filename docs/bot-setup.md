# Discord Bot Setup

- Go to the [Discord Developer Portal](https://discord.com/developers/applications)
- Click **New Application**, give it a name, and save
- Go to the **Bot** tab and click **Reset Token** to generate a bot token
- Copy the token and set it as `DOPPELGANGER_DISCORD__TOKEN` in your `.env`
- Upload [assets/bot.jpg](assets/bot.jpg) to profile picture.

On the **Bot** tab:
- Enable **Server Members Intent** - not required, but useful for future user lookup
- Enable **Message Content Intent** - not required for slash commands, but enable if you plan to add prefix commands

Set permissions and invite:
- Go to the **OAuth2** tab
- Under **Scopes**, select `bot` and `applications.commands`
- Under **Bot Permissions**, select: `Connect`, `Speak`, `Use Voice Activity`
- Copy the generated invite URL and open in browser to add bot to the server

Get guild and role IDs:
- In Discord, enable **Developer Mode** (Settings > Advanced > Developer Mode)
- set `DOPPELGANGER_DISCORD__GUILD_ID` in `.env` - Right-click server name and **Copy Server ID**
- set `DOPPELGANGER_DISCORD__REQUIRED_ROLE_ID` (optional) - right-click role you want to restrict usage to and **Copy Role ID**

Verify
- Start API `make dev`
- Bot will be online with a `Listening | /say` status. Slash commands sync to the guild on startup.
