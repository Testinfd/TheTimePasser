import csv, json, asyncio, io, logging
import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import ADMINS, CHANNELS, LOG_CHANNEL
from database.ia_filterdb import col, sec_col, save_file, unpack_new_file_id
from database.users_chats_db import db
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid

async def export_files_to_json(collection, file_path=None):
    """Export files from MongoDB to JSON"""
    cursor = collection.find({})
    files = []
    
    # Convert MongoDB documents to JSON serializable dict
    for doc in await cursor.to_list(None):
        # Remove MongoDB-specific ID field if it exists
        if "_id" in doc:
            del doc["_id"]
        files.append(doc)
    
    if file_path:
        # Save to file
        with open(file_path, 'w') as f:
            json.dump(files, f, default=str, indent=2)
    
    return files

async def export_files_to_csv(collection, file_path=None):
    """Export files from MongoDB to CSV"""
    cursor = collection.find({})
    files = await cursor.to_list(None)
    
    if not files:
        return []
    
    # Get field names from the first document
    fields = list(files[0].keys())
    if "_id" in fields:
        fields.remove("_id")  # Remove MongoDB ID
    
    # Convert to CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    
    for doc in files:
        # Convert ObjectId to string for CSV compatibility
        row = {k: str(v) if k == "_id" else v for k, v in doc.items()}
        writer.writerow(row)
    
    if file_path:
        with open(file_path, 'w', newline='') as f:
            f.write(output.getvalue())
    
    return output.getvalue()

async def import_files_from_json(json_data, collection):
    """Import files from JSON to MongoDB"""
    if isinstance(json_data, str):
        try:
            files = json.loads(json_data)
        except json.JSONDecodeError:
            # Try reading from file path
            with open(json_data, 'r') as f:
                files = json.load(f)
    else:
        # Assume it's already a Python list/dict
        files = json_data
    
    success_count = 0
    error_count = 0
    
    for file_data in files:
        try:
            # Check if file already exists to avoid duplicates
            existing = await collection.find_one({"file_id": file_data["file_id"]})
            if not existing:
                await collection.insert_one(file_data)
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            logging.error(f"Error importing file: {str(e)}")
            error_count += 1
    
    return success_count, error_count

async def import_files_from_csv(csv_data, collection):
    """Import files from CSV to MongoDB"""
    if isinstance(csv_data, str):
        try:
            # Check if it's CSV content or a file path
            if '\n' in csv_data:
                file_obj = io.StringIO(csv_data)
            else:
                file_obj = open(csv_data, 'r')
        except:
            return 0, 0
    else:
        # Assume it's a file-like object
        file_obj = csv_data
    
    reader = csv.DictReader(file_obj)
    files = list(reader)
    
    success_count = 0
    error_count = 0
    
    for file_data in files:
        try:
            # Check if file already exists
            existing = await collection.find_one({"file_id": file_data["file_id"]})
            if not existing:
                await collection.insert_one(file_data)
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            logging.error(f"Error importing file from CSV: {str(e)}")
            error_count += 1
    
    if isinstance(csv_data, str) and '\n' not in csv_data:
        file_obj.close()
    
    return success_count, error_count

# Add commands for the bot to use these features
@Client.on_message(filters.command("exportfiles") & filters.user(ADMINS))
async def export_all_files(bot, message):
    """Command handler to export all files"""
    chat_id = message.chat.id
    # Send initial message
    status = await message.reply("Exporting files... This may take some time.")
    
    try:
        # Create a JSON file
        temp_file = f"temp_export_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        
        # Export from both collections if using multiple databases
        files = await export_files_to_json(col, temp_file)
        file_count = len(files)
        
        # Send the file to the admin
        await bot.send_document(
            chat_id=chat_id,
            document=temp_file,
            caption=f"Exported {file_count} files as JSON.",
            file_name=f"filter_bot_files_{datetime.datetime.now().strftime('%Y%m%d')}.json"
        )
        
        # Delete temp file
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        await status.edit_text(f"Successfully exported {file_count} files.")
    except Exception as e:
        logging.error(f"Error exporting files: {str(e)}")
        await status.edit_text(f"Error exporting files: {str(e)}")

@Client.on_message(filters.command("importfiles") & filters.user(ADMINS) & filters.document)
async def import_files_cmd(bot, message):
    """Command handler to import files from a document"""
    chat_id = message.chat.id
    
    # Check if there's a file attached
    if not message.document:
        await message.reply("Please attach a JSON or CSV file with the command.")
        return
    
    # Send initial message
    status = await message.reply("Importing files... This may take some time.")
    
    try:
        # Download the file
        file_path = await bot.download_media(message.document)
        
        # Check file type
        if file_path.endswith('.json'):
            success, errors = await import_files_from_json(file_path, col)
        elif file_path.endswith('.csv'):
            success, errors = await import_files_from_csv(file_path, col)
        else:
            await status.edit_text("Unsupported file format. Please use JSON or CSV.")
            # Delete downloaded file
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
            return
        
        # Delete downloaded file
        import os
        if os.path.exists(file_path):
            os.remove(file_path)
        
        await status.edit_text(f"Import completed: {success} files imported successfully, {errors} errors.")
    except Exception as e:
        logging.error(f"Error importing files: {str(e)}")
        await status.edit_text(f"Error importing files: {str(e)}")

async def fetch_batch_file_info(bot, channel_id, batch_size=100, max_files=1000):
    """Fetch file info from a channel in batches"""
    file_count = 0
    files_data = []
    last_msg_id = 0
    
    # Maximum messages to fetch (to prevent excessive API usage)
    max_iterations = max_files // batch_size
    
    for _ in range(max_iterations):
        try:
            # Get messages from the channel in batches
            messages = await bot.get_messages(
                chat_id=channel_id,
                offset_id=last_msg_id,
                reverse=True,
                limit=batch_size
            )
            
            if not messages:
                break
            
            last_msg_id = messages[-1].id
            
            for msg in messages:
                if msg.media:
                    # Process document, video, audio, etc.
                    file_info = await process_media_message(msg)
                    if file_info:
                        files_data.append(file_info)
                        file_count += 1
            
            # If we've reached the desired file count
            if file_count >= max_files:
                break
                
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except Exception as e:
            logging.error(f"Error fetching files from channel: {str(e)}")
            break
    
    return files_data

async def process_media_message(message):
    """Extract file info from a media message"""
    media = None
    media_type = None
    
    # Check the type of media
    if message.document:
        media = message.document
        media_type = "document"
    elif message.video:
        media = message.video
        media_type = "video"
    elif message.audio:
        media = message.audio
        media_type = "audio"
    elif message.animation:
        media = message.animation
        media_type = "animation"
    else:
        return None
    
    # Extract file info
    file_info = {
        "file_id": media.file_id,
        "file_name": getattr(media, "file_name", f"Unnamed {media_type}"),
        "file_size": media.file_size,
        "caption": message.caption.html if message.caption else None,
        "mime_type": getattr(media, "mime_type", None),
        "media_type": media_type,
        "timestamp": datetime.datetime.now().timestamp()
    }
    
    return file_info

@Client.on_message(filters.command("batchchannel") & filters.user(ADMINS))
async def batch_channel_import(bot, message):
    """Import files from a channel in batch"""
    # Check command format
    if len(message.command) < 2:
        await message.reply("Please provide a channel ID or username after the command.")
        return
    
    channel_id = message.command[1]
    max_files = 500  # Default
    
    if len(message.command) >= 3:
        try:
            max_files = int(message.command[2])
        except ValueError:
            pass
    
    # Send initial message
    status = await message.reply(f"Fetching up to {max_files} files from the channel. This may take some time...")
    
    try:
        # Fetch files from the channel
        files_data = await fetch_batch_file_info(bot, channel_id, max_files=max_files)
        
        if not files_data:
            await status.edit_text("No media files found in the specified channel.")
            return
        
        # Save to database
        success_count = 0
        error_count = 0
        
        for file_info in files_data:
            try:
                # Adapt the file info to match format expected by save_file
                media_dict = {
                    "file_id": file_info["file_id"],
                    "file_name": file_info["file_name"],
                    "file_size": file_info["file_size"],
                    "caption": file_info["caption"]
                }
                
                # Use the existing save_file function
                success, result = await save_file(media_dict)
                if success:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logging.error(f"Error saving file: {str(e)}")
                error_count += 1
        
        await status.edit_text(f"Batch import completed: {success_count} files imported successfully, {error_count} errors.")
    except Exception as e:
        logging.error(f"Error in batch channel import: {str(e)}")
        await status.edit_text(f"Error in batch import: {str(e)}")

@Client.on_message(filters.command("bulkforward") & filters.user(ADMINS))
async def bulk_forward(bot, message):
    """Forward multiple files to a target channel"""
    # Check command format
    if len(message.command) < 3:
        await message.reply("Usage: /bulkforward [source_channel_id] [target_channel_id] [count(optional)]")
        return
    
    source_channel = message.command[1]
    target_channel = message.command[2]
    max_files = 100  # Default
    
    if len(message.command) >= 4:
        try:
            max_files = int(message.command[3])
        except ValueError:
            pass
    
    # Send initial message
    status = await message.reply(f"Forwarding up to {max_files} files from {source_channel} to {target_channel}. This may take some time...")
    
    try:
        # Get messages from the source channel
        file_count = 0
        last_msg_id = 0
        
        for _ in range((max_files // 100) + 1):
            try:
                # Get messages from the channel in batches
                messages = await bot.get_messages(
                    chat_id=source_channel,
                    offset_id=last_msg_id,
                    reverse=True,
                    limit=100
                )
                
                if not messages:
                    break
                
                last_msg_id = messages[-1].id
                
                for msg in messages:
                    if msg.media:
                        # Forward the message
                        await bot.forward_messages(
                            chat_id=target_channel,
                            from_chat_id=source_channel,
                            message_ids=msg.id
                        )
                        file_count += 1
                        
                        # Add a small delay to avoid hitting rate limits
                        await asyncio.sleep(0.5)
                    
                    # If we've reached the desired file count
                    if file_count >= max_files:
                        break
                
                if file_count >= max_files:
                    break
                    
            except FloodWait as e:
                await asyncio.sleep(e.x)
            except Exception as e:
                logging.error(f"Error forwarding files: {str(e)}")
                await status.edit_text(f"Error while forwarding: {str(e)}")
                return
        
        await status.edit_text(f"Successfully forwarded {file_count} files to the target channel.")
    except Exception as e:
        logging.error(f"Error in bulk forward operation: {str(e)}")
        await status.edit_text(f"Error in bulk forward operation: {str(e)}") 