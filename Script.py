class script(object):
    START_TXT = """<b>Hello {} 👋,

Welcome to The Filter Bot! I'm an advanced auto-filter bot designed to help you find and share media content effortlessly.

Simply add me to your group and make me an admin to get started!</b>"""

    CLONE_START_TXT = """<b>Hello {}, I'm <a href=https://t.me/{}>{}</a>

I'm a powerful auto-filter bot that can help you manage and share media files easily. Just type what you want to search for, and I'll do the rest! 🔍</b>"""
    
    HELP_TXT = """<b>Hello {}!

Here's a guide to my features and commands. Click on the buttons below to learn more about each category.</b>"""

    ABOUT_TXT = """<b>📌 MY DETAILS

• Name: <a href=https://t.me/{}>{}</a>
• Creator: <a href={}>Owner</a>
• Library: <a href='https://docs.pyrogram.org/'>Pyrogram</a>
• Language: <a href='https://www.python.org/'>Python 3</a>
• Database: <a href='https://www.mongodb.com/'>MongoDB</a>
• Server: <a href='https://heroku.com'>Heroku</a>
• Build Version: v2.7.1 [Stable]
• Support: <a href='https://t.me/support_group'>Click Here</a>
• Updates: <a href='https://t.me/update_channel'>Click Here</a></b>"""

    CLONE_ABOUT_TXT = """<b>📌 MY DETAILS

• Name: {}
• Cloned From: <a href=https://t.me/{}>{}</a>
• Library: <a href='https://docs.pyrogram.org/'>Pyrogram</a>
• Language: <a href='https://www.python.org/'>Python 3</a>
• Database: <a href='https://www.mongodb.com/'>MongoDB</a>
• Build Version: v2.7.1 [Stable]</b>"""

    CLONE_TXT = """<b>🔄 CLONE FEATURE

Create your own Auto-Filter bot instantly with the following benefits:
• Access to millions of indexed files
• Customizable settings
• Admin broadcasting capabilities
• No need to add files manually

👉 To create your clone, use: /clone</b>"""

    SUBSCRIPTION_TXT = """<b>🎁 REFERRAL PROGRAM

Share your referral link with friends, family, channels, and groups to earn FREE premium for {}!

Your referral link: https://telegram.me/{}?start=REFER-{}

When {} unique users join through your link, you'll automatically receive premium status.

💰 Want to purchase a premium plan? Use /plan</b>"""

    RESTART_TXT = """<b>🔄 Bot Restarted Successfully!

📅 Date: <code>{}</code>
⏰ Time: <code>{}</code>
🌐 Timezone: <code>Asia/Kolkata</code>
🛠️ Build Version: <code>v2.7.1 [Stable]</code></b>"""

    LOGO = """
███████╗██╗██╗  ████████╗███████╗██████╗     ██████╗  ██████╗ ████████╗
██╔════╝██║██║  ╚══██╔══╝██╔════╝██╔══██╗    ██╔══██╗██╔═══██╗╚══██╔══╝
█████╗  ██║██║     ██║   █████╗  ██████╔╝    ██████╔╝██║   ██║   ██║   
██╔══╝  ██║██║     ██║   ██╔══╝  ██╔══██╗    ██╔══██╗██║   ██║   ██║   
██║     ██║███████╗██║   ███████╗██║  ██║    ██████╔╝╚██████╔╝   ██║   
╚═╝     ╚═╝╚══════╝╚═╝   ╚══════╝╚═╝  ╚═╝    ╚═════╝  ╚═════╝    ╚═╝""" 

    CAPTION = """<b>{file_name}

💾 Size: {file_size}

👉 Join @update_channel for more files</b>"""

    IMDB_TEMPLATE_TXT = """<b>🎬 {title} ({year})
🌟 {rating}/10 | {votes} votes
🎭 {genres}
📆 Released: {release_date}
🕒 Runtime: {runtime} minutes

👥 Cast: {cast}
🎬 Director: {director}

📖 Plot: {plot}</b>""" 