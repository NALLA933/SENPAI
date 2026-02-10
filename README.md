# Sᴇɴᴘᴀɪ Wᴀɪғᴜ Bᴏᴛ

A Telegram bot for collecting anime characters. Guess characters that appear in your group chats and add them to your harem!

## Features

- 🎮 **Character Collection**: Guess characters and add them to your collection
- 💰 **Economy System**: Earn coins by guessing characters, use them in the shop
- 🏪 **Character Shop**: Buy characters with your earned coins
- 🎁 **Gifting System**: Gift characters to other users
- 📊 **Leaderboards**: Compete with other users and groups
- 🔍 **Search**: Search for characters by name or anime
- 🎫 **Redeem Codes**: Create and redeem codes for rewards
- 🛡️ **Admin Controls**: Full admin panel for managing the bot

## Rarity System

| Level | Name | Emoji |
|-------|------|-------|
| 1 | Common | ⚪ |
| 2 | Rare | 🔵 |
| 3 | Legendary | 🟡 |
| 4 | Special | 💮 |
| 5 | Ancient | 👹 |
| 6 | Celestial | 🎐 |
| 7 | Epic | 🔮 |
| 8 | Cosmic | 🪐 |
| 9 | Nightmare | ⚰️ |
| 10 | Frostborn | 🌬️ |
| 11 | Valentine | 💝 |
| 12 | Spring | 🌸 |
| 13 | Tropical | 🏖️ |
| 14 | Kawaii | 🍭 |
| 15 | Hybrid | 🧬 |

## Commands

### Game Commands
- `/guess <name>` - Guess the character name
- `/harem` - View your character collection
- `/fav <id>` - Set your favorite character

### Economy Commands
- `/balance` - Check your coin balance
- `/pay <user> <amount>` - Pay coins to another user
- `/shop` - Browse the character shop
- `/buy <item>` - Buy a character from the shop

### Search Commands
- `/search <name>` - Search for characters
- `/anime <name>` - Search characters by anime
- `/id <id>` - Get character info by ID

### Leaderboard Commands
- `/leaderboard` - View leaderboards
- `/top` - Top 10 users
- `/grouptop` - Top groups

### Gift Commands
- `/gift <id> <user>` - Gift a character to another user
- `/redeem <code>` - Redeem a code for rewards

### Settings
- `/smode` - Filter harem by rarity
- `/changetime <seconds>` - Change spawn frequency (Admin)
- `/setrarity` - Manage rarity settings (Admin)

### Admin Commands
- `/upload` - Upload new characters
- `/uploadurl` - Upload character with URL
- `/deletechar` - Delete a character
- `/give` - Give character to user
- `/givecoins` - Give coins to user
- `/broadcast` - Broadcast to all users
- `/backup` - Create database backup
- `/restore` - Restore from backup
- `/eval` - Execute Python code

## Deployment

### Local Deployment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/senpai-waifu-bot.git
cd senpai-waifu-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Run the bot:
```bash
python3 -m shivu
```

### Heroku Deployment

1. Fork this repository
2. Create a new Heroku app
3. Add your environment variables in Heroku settings
4. Deploy from GitHub

### Docker Deployment

1. Build the image:
```bash
docker build -t senpai-waifu-bot .
```

2. Run the container:
```bash
docker run -d --env-file .env senpai-waifu-bot
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | Yes |
| `BOT_USERNAME` | Your bot's username | Yes |
| `API_ID` | Telegram API ID from my.telegram.org | Yes |
| `API_HASH` | Telegram API Hash from my.telegram.org | Yes |
| `OWNER_ID` | Your Telegram user ID | Yes |
| `SUDO_USERS` | Comma-separated list of sudo user IDs | No |
| `GROUP_ID` | Main group ID for the bot | Yes |
| `CHARA_CHANNEL_ID` | Channel ID for character updates | Yes |
| `MONGO_URL` | MongoDB connection string | Yes |
| `IMGBB_API_KEY` | ImgBB API key for image uploads | No |
| `SUPPORT_CHAT` | Support group username | No |
| `UPDATE_CHAT` | Updates channel username | No |

## Database Structure

The bot uses MongoDB with the following collections:
- `anime_characters` - Character data
- `user_collection` - User data and collections
- `user_totals` - User statistics
- `group_user_totals` - Group-specific user stats
- `top_global_groups` - Group leaderboards
- `pm_users` - PM user list for broadcasts
- `user_balance` - User coin balances

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Original concept by [TeamNexus](https://t.me/TeamNexus)
- Developed with ❤️ for the anime community

## Support

For support, join our [Support Group](https://t.me/your_support_group) or contact the bot owner.

---

**Note**: This bot is for educational purposes. Please respect copyright and terms of service.
