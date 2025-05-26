<p align="center">
  <img src="https://github.com/Testinfd/TheTimePasser/raw/main/logo.png" alt="Filter Bot Logo" width="200">
</p>
<h1 align="center">
  THE FILTER BOT
</h1>

<p align="center">
  <a href="https://github.com/Testinfd/TheTimePasser/stargazers"><img src="https://img.shields.io/github/stars/Testinfd/TheTimePasser?style=flat-square&color=yellow" alt="Stars"></a>
  <a href="https://github.com/Testinfd/TheTimePasser/fork"><img src="https://img.shields.io/github/forks/Testinfd/TheTimePasser?style=flat-square&color=orange" alt="Forks"></a>
  <a href="https://github.com/Testinfd/TheTimePasser/issues"><img src="https://img.shields.io/github/issues/Testinfd/TheTimePasser?style=flat-square&color=green" alt="Issues"></a>
  <a href="https://github.com/Testinfd/TheTimePasser/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Testinfd/TheTimePasser?style=flat-square&color=blue" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9-blue.svg?style=flat-square&logo=python" alt="Python"></a>
  <a href="https://github.com/Testinfd/TheTimePasser/commits/main"><img src="https://img.shields.io/github/last-commit/Testinfd/TheTimePasser?style=flat-square&color=red" alt="Last Commit"></a>
</p>

<p align="center">
An advanced auto-filter Telegram bot with many powerful features.
</p>

## 🔰 Making Your Bot Admin in Force Subscribe Channel

To make your bot function properly with force subscribe feature, you need to add your bot as admin in the force subscribe channel with full admin rights. Here's how:

1. Open your Telegram app and go to your force subscribe channel
2. Click on the channel name at the top to access channel info
3. Select "Administrators"
4. Click "Add Admin" and search for your bot's username
5. Enable all permissions for the bot, especially:
   - Post Messages
   - Edit Messages
   - Delete Messages
   - Restrict Members
   - Invite Users via Link
   - Add New Admins

> ⚠️ **Important**: Without proper admin permissions, your force subscribe feature may not work correctly.

## ✨ Features

<details>
<summary>Click to expand feature list</summary>

- **Core Features**
  - ✅ Multiple Database Support
  - ✅ Auto-Filter for files
  - ✅ Manual Filter support
  - ✅ Powerful clone functionality
  - ✅ File indexing with skip options
  - ✅ Connection with multiple groups
  - ✅ Support for sending all matched results

- **Premium Features**
  - ✅ Premium plan support
  - ✅ Referral system for earning premium
  - ✅ Customizable premium benefits

- **Content Management**
  - ✅ Rename files with custom thumbnails
  - ✅ Custom file captions
  - ✅ Streaming feature with multiple player support
  - ✅ Batch file link generation
  - ✅ Telegraph link generation
  - ✅ Language, season, quality, episode filters

- **Channel & Group Management**
  - ✅ Custom force subscribe
  - ✅ Auto-approve new members
  - ✅ Request-to-join with auto file send
  - ✅ Global and group-specific filters

- **Additional Tools**
  - ✅ AI spell check for searches
  - ✅ URL shortener integration
  - ✅ Token verification system
  - ✅ PM search functionality
  - ✅ Custom tutorial buttons
  - ✅ Bot PM auto-delete
  - ✅ IMDB integration with custom templates

- **Admin Controls**
  - ✅ Detailed logs and statistics
  - ✅ User management (ban/unban)
  - ✅ Broadcast messages to users and groups
  - ✅ Fine-grained control over all features

</details>

## 🤖 Commands

<details>
<summary>View all available commands</summary>

### User Commands
- `/start` - Start the bot
- `/help` - Get help and command information
- `/plan` - Check premium plan details
- `/myplan` - View your current plan status
- `/search` - Search for files from various sources
- `/imdb` - Fetch info from IMDB
- `/info` - Get user information
- `/id` - Get Telegram IDs
- `/connect` - Connect to PM for file search
- `/batch` - Create link for multiple posts
- `/link` - Create link for a single post
- `/font` - Convert text to stylish fonts
- `/telegraph` - Generate telegraph link for files under 5MB
- `/stream` - Generate streaming and download links

### Filter Commands
- `/filter` - Add manual filters
- `/filters` - View all filters
- `/del` - Delete a filter
- `/delall` - Delete all filters
- `/gfilter` - Add global filters
- `/gfilters` - View all global filters
- `/delg` - Delete a global filter
- `/delallg` - Delete all global filters

### Admin Commands
- `/logs` - Get recent error logs
- `/stats` - Check database file statistics
- `/index` - Index files from your channel
- `/setskip` - Set number of messages to skip during indexing
- `/deleteall` - Delete all indexed files
- `/delete` - Delete specific files from index
- `/users` - Get list of bot users
- `/chats` - Get list of connected chats
- `/broadcast` - Broadcast message to all users
- `/grp_broadcast` - Broadcast to all connected groups
- `/restart` - Restart the bot
- `/leave` - Make bot leave a chat
- `/disable` - Disable a chat
- `/enable` - Re-enable a chat
- `/ban` - Ban a user
- `/unban` - Unban a user
- `/clone` - Create your own clone bot

### Shortlink Commands
- `/shortlink` - Set URL shortener for your group
- `/setshortlinkon` - Enable shortlink in your group
- `/setshortlinkoff` - Disable shortlink in your group
- `/shortlink_info` - Check shortlink details
- `/set_tutorial` - Set tutorial link for shortener
- `/remove_tutorial` - Remove tutorial link

### Rename Commands
- `/rename` - Rename files
- `/set_caption` - Add caption for renamed files
- `/see_caption` - View your saved caption
- `/del_caption` - Delete your saved caption
- `/set_thumb` - Set thumbnail for renamed files
- `/view_thumb` - View your saved thumbnail
- `/del_thumb` - Delete your saved thumbnail

### Force Subscribe Commands
- `/fsub` - Add force subscribe channel
- `/nofsub` - Remove force subscribe

### Premium Commands
- `/add_premium` - Add user to premium list (admin only)
- `/remove_premium` - Remove user from premium list (admin only)

### Maintenance Commands
- `/deletefiles` - Delete PreDVD and CamRip files
- `/connections` - View all connected groups
- `/settings` - Open settings menu
- `/channel` - Get list of connected channels
- `/set_template` - Set custom IMDB template
- `/purgerequests` - Delete all join requests from database
- `/totalrequests` - Get total number of join requests

</details>

## ⚙️ Environment Variables

<details>
<summary>Required Variables</summary>

- `BOT_TOKEN`: Your Telegram Bot Token from [BotFather](https://telegram.dog/BotFather)
- `API_ID`: Your API ID from [my.telegram.org](https://my.telegram.org/apps)
- `API_HASH`: Your API Hash from [my.telegram.org](https://my.telegram.org/apps)
- `CHANNELS`: Channel or group username/ID for file indexing (space-separated for multiple)
- `ADMINS`: Username or ID of admins (space-separated for multiple)
- `DATABASE_URI`: [MongoDB](https://www.mongodb.com) connection URI
- `LOG_CHANNEL`: Channel ID for logging bot activities

</details>

<details>
<summary>Optional Variables</summary>

- `PICS`: URLs of photos for start message (space-separated)
- `AUTH_USERS`: Additional authorized users (space-separated IDs)
- `AUTH_CHANNEL`: Force subscribe channel ID
- `CUSTOM_FILE_CAPTION`: Custom caption for files
- `IMDB_TEMPLATE`: Custom template for IMDB results
- `SPELL_CHECK_REPLY`: Enable/disable spell check (True/False)
- `SHORTLINK_URL`: URL Shortener domain
- `SHORTLINK_API`: URL Shortener API key
- `MULTIPLE_DATABASE`: Enable multiple database support (True/False)
- `PREMIUM_AND_REFERAL_MODE`: Enable premium and referral system (True/False)
- `VERIFY`: Enable verification system (True/False)
- `STREAM_MODE`: Enable streaming feature (True/False)
- `RENAME_MODE`: Enable rename feature (True/False)
- `AUTO_APPROVE_MODE`: Enable auto-approve for join requests (True/False)

</details>

## 🚀 Deployment

<details>
<summary><b>Deploy to Heroku</b></summary>

1. Fork this repository
2. Go to your forked repository settings -> secrets
3. Create the required secrets mentioned in environment variables
4. Go to Heroku and create a new app
5. Connect your GitHub repository to Heroku
6. Deploy with the Procfile

</details>

<details>
<summary><b>Deploy to Koyeb</b></summary>

The fastest way to deploy the application is to click the Deploy to Koyeb button below:

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=git&repository=github.com/Testinfd/TheTimePasser&branch=main&name=TheTimePasser)

</details>

<details>
<summary><b>Deploy to Render</b></summary>

**Use these commands:**

- Build Command: `pip3 install -U -r requirements.txt`
- Start Command: `python3 bot.py`

Go to https://uptimerobot.com/ and add a monitor to keep your bot alive.

**Click the button below to deploy to Render:**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Testinfd/TheTimePasser)

</details>

<details>
<summary><b>Deploy to VPS/Local</b></summary>

```bash
# Clone the repository
git clone https://github.com/Testinfd/TheTimePasser

# Change directory
cd TheTimePasser

# Install requirements
pip3 install -U -r requirements.txt

# Edit info.py with your values
nano info.py

# Run the bot
python3 bot.py
```

</details>

## 🌟 Support & Updates

<a href="https://telegram.dog/support_group"><img src="https://img.shields.io/badge/Join-Support%20Group-blue.svg?style=for-the-badge&logo=Telegram"></a> <a href="https://telegram.dog/update_channel"><img src="https://img.shields.io/badge/Join-Update%20Channel-blue.svg?style=for-the-badge&logo=Telegram"></a>

## 🙏 Acknowledgements

- Thanks to [VJBots](https://github.com/VJBots/VJ-FILTER-BOT) for the original version that this project is based on
- All the developers who have contributed to this project
- Special thanks to all users who reported bugs and suggested features

## ⚠️ Disclaimer

[![GNU Affero General Public License 2.0](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.en.html#header)    
Licensed under [GNU AGPL 2.0](https://github.com/Testinfd/TheTimePasser/blob/main/LICENSE).
Selling the code to other people for money is **strictly prohibited**.

## 👨‍💻 Contributors

<a href="https://github.com/Testinfd/TheTimePasser/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Testinfd/TheTimePasser" />
</a>
