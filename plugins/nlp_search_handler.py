import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main.bot import MainBot
from main.nlp_search import nlp_search
from database.tiered_access import tiered_access
from info import ADMINS
import asyncio

logger = logging.getLogger(__name__)

@MainBot.on_message(filters.command("nlpsearch"))
async def nlp_search_command(client, message):
    """Handle natural language search queries"""
    try:
        # Check if user has access to NLP search
        user_id = message.from_user.id
        can_use_nlp = await tiered_access.can_use_feature(user_id, "nlp_search")
        
        if not can_use_nlp and user_id not in ADMINS:
            # User cannot use NLP search
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Upgrade Plan", callback_data="upgrade_plan")]
            ])
            await message.reply(
                "⭐ **Premium Feature**\nNatural language search is available only for premium users. "
                "Please upgrade your plan to access this feature.",
                reply_markup=keyboard
            )
            return
            
        # Get search query
        if len(message.text.split()) <= 1:
            await message.reply(
                "Please provide a search query.\n\nExample: `/nlpsearch latest action movies with Tom Cruise`"
            )
            return
            
        query = message.text.split(" ", 1)[1].strip()
        
        if len(query) < 3:
            await message.reply("Search query is too short. Please provide a more detailed query.")
            return
            
        # Send typing action
        await client.send_chat_action(message.chat.id, "typing")
        
        # Show processing message
        processing_msg = await message.reply("🔍 Processing your natural language query...")
        
        # Perform search
        result = await nlp_search.search(user_id, query)
        
        if result["error"]:
            await processing_msg.edit(f"❌ Error: {result['error']}")
            return
            
        files = result["results"]
        
        if not files:
            await processing_msg.edit(f"No results found for: `{query}`")
            return
            
        # Format results
        msg = f"🔍 **NLP Search Results**\n\n"
        msg += f"Query: `{query}`\n"
        msg += f"Found {len(files)} results\n\n"
        
        # Show top 10 results
        for i, file in enumerate(files[:10], 1):
            file_name = file.get("file_name", "Unknown")
            file_size = file.get("size", 0)
            
            # Format file size
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size/1024:.2f} KB"
            else:
                size_str = f"{file_size/(1024*1024):.2f} MB"
                
            msg += f"{i}. `{file_name}` ({size_str})\n"
            
        if len(files) > 10:
            msg += f"\n... and {len(files) - 10} more results."
            
        # Create keyboard with file links
        buttons = []
        for i, file in enumerate(files[:10], 1):
            file_id = file.get("file_id")
            if file_id:
                buttons.append([InlineKeyboardButton(f"{i}. {file.get('file_name', 'File')}", callback_data=f"get_file_{file_id}")])
                
        if len(files) > 10:
            buttons.append([InlineKeyboardButton("Show More", callback_data=f"show_more_{query}")])
            
        keyboard = InlineKeyboardMarkup(buttons)
        
        # Edit processing message with results
        await processing_msg.edit(msg, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in NLP search: {e}")
        await message.reply(f"An error occurred while processing your search: {str(e)}")

@MainBot.on_message(filters.command("nlpstatus") & filters.user(ADMINS))
async def nlp_status_command(client, message):
    """Show NLP search status for admins"""
    try:
        # Get some stats about NLP search usage
        # This is a placeholder - you would need to implement analytics tracking
        
        msg = "🔍 **NLP Search Status**\n\n"
        msg += "Status: ✅ Active\n"
        msg += "Backend: NLTK\n\n"
        
        # Create keyboard for admin actions
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Enable for All Users", callback_data="nlp_enable_all")],
            [InlineKeyboardButton("Disable for All Users", callback_data="nlp_disable_all")],
            [InlineKeyboardButton("View Usage Stats", callback_data="nlp_stats")]
        ])
        
        await message.reply(msg, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in NLP status: {e}")
        await message.reply(f"Error: {str(e)}")

# Add callback handlers for NLP search buttons
@MainBot.on_callback_query(filters.regex(r"^get_file_(.+)"))
async def get_file_callback(client, callback_query):
    """Handle file selection from NLP search results"""
    try:
        file_id = callback_query.data.split("_", 2)[2]
        
        # Here you would implement the logic to send the file to the user
        # This depends on how your bot handles file sending
        
        await callback_query.answer("Processing your request...")
        
        # This is a placeholder - you would need to implement file sending
        await callback_query.message.reply(f"You selected file with ID: {file_id}")
        
    except Exception as e:
        logger.error(f"Error in get file callback: {e}")
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)

@MainBot.on_callback_query(filters.regex(r"^show_more_(.+)"))
async def show_more_callback(client, callback_query):
    """Handle showing more NLP search results"""
    try:
        query = callback_query.data.split("_", 2)[2]
        user_id = callback_query.from_user.id
        
        await callback_query.answer("Loading more results...")
        
        # Perform search again
        result = await nlp_search.search(user_id, query, limit=50)
        
        if result["error"]:
            await callback_query.message.reply(f"❌ Error: {result['error']}")
            return
            
        files = result["results"][10:30]  # Get next 20 results
        
        if not files:
            await callback_query.message.reply("No more results to show.")
            return
            
        # Format results
        msg = f"🔍 **More NLP Search Results**\n\n"
        msg += f"Query: `{query}`\n\n"
        
        for i, file in enumerate(files, 11):  # Start numbering from 11
            file_name = file.get("file_name", "Unknown")
            file_size = file.get("size", 0)
            
            # Format file size
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size/1024:.2f} KB"
            else:
                size_str = f"{file_size/(1024*1024):.2f} MB"
                
            msg += f"{i}. `{file_name}` ({size_str})\n"
            
        # Create keyboard with file links
        buttons = []
        for i, file in enumerate(files, 11):
            file_id = file.get("file_id")
            if file_id:
                buttons.append([InlineKeyboardButton(f"{i}. {file.get('file_name', 'File')}", callback_data=f"get_file_{file_id}")])
                
        keyboard = InlineKeyboardMarkup(buttons)
        
        # Send new message with more results
        await callback_query.message.reply(msg, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in show more callback: {e}")
        await callback_query.answer(f"Error: {str(e)}", show_alert=True) 