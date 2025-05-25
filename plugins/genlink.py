import re, asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserAlreadyParticipant, FloodWait
from database.users_chats_db import db
from info import CHANNELS, ADMINS
from utils import get_size
import base64

@Client.on_message(filters.command(['link', 'plink']))
async def gen_link(bot, message):
    if message.from_user.id not in ADMINS:
        return
    links = ""
    pr_links = ""
    if message.reply_to_message:
        message = message.reply_to_message
    chat_id = message.chat.id
    if chat_id in CHANNELS:
        channel = f"{CHANNELS.index(chat_id)}"
        chat_id=f"-100{chat_id}"
    else:
        channel = "0"
    msg_id = message.id
    cmd_link = "plink" if message.text.startswith('/plink') else "link"
    await message.reply_text(
        f"<b>Here is your link</b>\n\n<code>/{cmd_link} {channel}_{msg_id}</code>\n\n<code>/batch {channel}_{msg_id} {channel}_{msg_id}</code>",
        protect_content=True
    )

@Client.on_message(filters.command(['batch']))
async def gen_link_batch(bot, message):
    if len(message.text.split()) != 3:
        return await message.reply("Use correct format.\nExample <code>/batch channel_id/message_id channel_id/message_id</code>.")
    links = ""
    pr_links = ""
    if message.from_user.id not in ADMINS:
        return
    if (" " in message.text) and (len(message.text.split()) == 3):
        cmd, first, last = message.text.split()
        regex = re.compile(r'(.*?)_(.*?)$')
        match = regex.match(first)
        if not match:
            return await message.reply("Use correct format.\nExample <code>/batch channel_id/message_id channel_id/message_id</code>.")
        f_chat_id, f_msg_id = match.groups()
        match = regex.match(last)
        if not match:
            return await message.reply("Use correct format.\nExample <code>/batch channel_id/message_id channel_id/message_id</code>.")
        l_chat_id, l_msg_id = match.groups()
        if f_chat_id != l_chat_id:
            return await message.reply("Chat ids not matching.")
        try:
            f_chat_id = int(f_chat_id)
            f_msg_id = int(f_msg_id)
            l_msg_id = int(l_msg_id)
        except:
            return await message.reply("Chat id and message id should be integers.")
        if f_msg_id > l_msg_id:
            return await message.reply("First message id should be less than or equal to last message id.")

        for idx, i in enumerate(range(f_chat_id, l_chat_id + 1)):
            try:
                link = f"https://t.me/c/{f_chat_id}/{i}"
                pr_link = f"https://t.me/c/{f_chat_id}/{i}?start=BATCH-{f_chat_id}_{f_msg_id}_{l_msg_id}"
                if cmd == "pbatch":
                    links += f"{idx+1}. {link}\n"
                    pr_links += f"{idx+1}. {pr_link}\n"
                else:
                    links += f"{idx+1}. {link}\n"
            except Exception as e:
                pass
        
        if len(links) > 4096:
            mm = await message.reply_text("The message is too long. Sending as a text file.")
            with open('links.txt', 'w') as f:
                f.write(links)
            await mm.delete()
            await message.reply_document('links.txt')
        else:
            if cmd == "pbatch":
                await message.reply_text(pr_links)
            else:
                await message.reply_text(links)
    else:
        return await message.reply("Use correct format.\nExample <code>/batch channel_id/message_id channel_id/message_id</code>.")
