import logging
import json
import csv
import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main.bot import MainBot
from info import ADMINS, DATABASE_NAME, OTHER_DB_URI
from database.db_helpers import get_mongo_client, get_async_mongo_client
from database.analytics import analytics_db

logger = logging.getLogger(__name__)

class BulkOperations:
    def __init__(self):
        """Initialize bulk operations handler"""
        self._client = get_async_mongo_client(OTHER_DB_URI)
        self.db = self._client[DATABASE_NAME]
        self.files = self.db.files
        self.temp_dir = "temp_exports"
        
        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        
    async def export_to_json(self, query=None, limit=None):
        """Export files to JSON format"""
        try:
            # Get files based on query or get all
            if query:
                cursor = self.files.find(query)
            else:
                cursor = self.files.find()
                
            # Apply limit if specified
            if limit:
                cursor = cursor.limit(limit)
                
            # Get all files
            files = await cursor.to_list(length=10000)
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.temp_dir}/export_{timestamp}.json"
            
            # Convert ObjectId to string for JSON serialization
            for file in files:
                if "_id" in file:
                    file["_id"] = str(file["_id"])
            
            # Write to file
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(files, f, indent=2, ensure_ascii=False)
                
            return {
                "success": True,
                "filename": filename,
                "count": len(files)
            }
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def export_to_csv(self, query=None, limit=None, fields=None):
        """Export files to CSV format"""
        try:
            # Get files based on query or get all
            if query:
                cursor = self.files.find(query)
            else:
                cursor = self.files.find()
                
            # Apply limit if specified
            if limit:
                cursor = cursor.limit(limit)
                
            # Get all files
            files = await cursor.to_list(length=10000)
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.temp_dir}/export_{timestamp}.csv"
            
            # Determine fields to export
            if not fields:
                # Use common fields if not specified
                fields = ["file_id", "file_name", "size", "caption", "type", "year", "season", "episode"]
            
            # Write to CSV file
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                
                for file in files:
                    # Convert ObjectId to string
                    if "_id" in file and "_id" in fields:
                        file["_id"] = str(file["_id"])
                    writer.writerow(file)
                
            return {
                "success": True,
                "filename": filename,
                "count": len(files)
            }
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def import_from_json(self, filename, update_existing=False):
        """Import files from JSON file"""
        try:
            # Read JSON file
            with open(filename, "r", encoding="utf-8") as f:
                files = json.load(f)
                
            if not isinstance(files, list):
                return {
                    "success": False,
                    "error": "Invalid JSON format. Expected a list of files."
                }
                
            # Track counts
            imported = 0
            skipped = 0
            updated = 0
            
            # Process each file
            for file in files:
                # Skip if no file_id
                if "file_id" not in file:
                    skipped += 1
                    continue
                    
                # Check if file exists
                existing = await self.files.find_one({"file_id": file["file_id"]})
                
                if existing:
                    if update_existing:
                        # Update existing file
                        await self.files.update_one(
                            {"file_id": file["file_id"]},
                            {"$set": file}
                        )
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Insert new file
                    await self.files.insert_one(file)
                    imported += 1
                    
            return {
                "success": True,
                "imported": imported,
                "updated": updated,
                "skipped": skipped,
                "total": len(files)
            }
        except Exception as e:
            logger.error(f"Error importing from JSON: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def import_from_csv(self, filename, update_existing=False):
        """Import files from CSV file"""
        try:
            # Read CSV file
            files = []
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    files.append(row)
                    
            # Track counts
            imported = 0
            skipped = 0
            updated = 0
            
            # Process each file
            for file in files:
                # Skip if no file_id
                if "file_id" not in file or not file["file_id"]:
                    skipped += 1
                    continue
                    
                # Convert empty strings to None
                for key, value in file.items():
                    if value == "":
                        file[key] = None
                    
                # Check if file exists
                existing = await self.files.find_one({"file_id": file["file_id"]})
                
                if existing:
                    if update_existing:
                        # Update existing file
                        await self.files.update_one(
                            {"file_id": file["file_id"]},
                            {"$set": file}
                        )
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Insert new file
                    await self.files.insert_one(file)
                    imported += 1
                    
            return {
                "success": True,
                "imported": imported,
                "updated": updated,
                "skipped": skipped,
                "total": len(files)
            }
        except Exception as e:
            logger.error(f"Error importing from CSV: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Create global instance
bulk_ops = BulkOperations()

# Command handlers
@MainBot.on_message(filters.command("export") & filters.user(ADMINS))
async def export_command(client, message):
    """Handle export command"""
    try:
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        # Parse arguments
        format_type = "json"  # Default format
        limit = 1000  # Default limit
        
        for arg in args:
            if arg.startswith("format="):
                format_type = arg.split("=")[1].lower()
            elif arg.startswith("limit="):
                try:
                    limit = int(arg.split("=")[1])
                except ValueError:
                    await message.reply("Invalid limit value. Using default limit of 1000.")
        
        # Send initial message
        status_msg = await message.reply(f"Exporting files to {format_type.upper()} format. Please wait...")
        
        # Perform export
        if format_type == "json":
            result = await bulk_ops.export_to_json(limit=limit)
        elif format_type == "csv":
            result = await bulk_ops.export_to_csv(limit=limit)
        else:
            await status_msg.edit(f"Unsupported format: {format_type}. Use 'json' or 'csv'.")
            return
            
        # Check result
        if result["success"]:
            # Upload file to chat
            await status_msg.edit(f"Export completed! Exported {result['count']} files. Uploading...")
            
            # Upload the file
            await client.send_document(
                chat_id=message.chat.id,
                document=result["filename"],
                caption=f"Exported {result['count']} files to {format_type.upper()} format."
            )
            
            # Delete the temporary file
            os.remove(result["filename"])
            
            await status_msg.edit("Export and upload completed!")
        else:
            await status_msg.edit(f"Export failed: {result['error']}")
    except Exception as e:
        logger.error(f"Error in export command: {e}")
        await message.reply(f"Error: {str(e)}")

@MainBot.on_message(filters.command("import") & filters.user(ADMINS))
async def import_command(client, message):
    """Handle import command"""
    try:
        # Check if file is attached
        if not message.reply_to_message or not message.reply_to_message.document:
            await message.reply(
                "Please reply to a JSON or CSV file to import.\n\n"
                "Example: `/import update=true` (reply to a file)"
            )
            return
            
        # Parse arguments
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        update_existing = False
        
        for arg in args:
            if arg.lower() in ["update=true", "update=yes", "update"]:
                update_existing = True
        
        # Get file info
        doc = message.reply_to_message.document
        file_name = doc.file_name
        
        # Check file extension
        if not file_name.lower().endswith((".json", ".csv")):
            await message.reply("Only JSON and CSV files are supported for import.")
            return
            
        # Send initial message
        status_msg = await message.reply(f"Downloading {file_name} for import...")
        
        # Download file
        file_path = f"{bulk_ops.temp_dir}/{file_name}"
        await message.reply_to_message.download(file_path)
        
        await status_msg.edit("File downloaded. Processing import...")
        
        # Perform import based on file type
        if file_name.lower().endswith(".json"):
            result = await bulk_ops.import_from_json(file_path, update_existing)
        else:  # CSV
            result = await bulk_ops.import_from_csv(file_path, update_existing)
            
        # Delete temporary file
        os.remove(file_path)
        
        # Check result
        if result["success"]:
            msg = f"Import completed!\n\n"
            msg += f"• Total files in import: {result['total']}\n"
            msg += f"• New files imported: {result['imported']}\n"
            
            if update_existing:
                msg += f"• Existing files updated: {result['updated']}\n"
            
            msg += f"• Files skipped: {result['skipped']}\n"
            
            await status_msg.edit(msg)
        else:
            await status_msg.edit(f"Import failed: {result['error']}")
    except Exception as e:
        logger.error(f"Error in import command: {e}")
        await message.reply(f"Error: {str(e)}")

@MainBot.on_message(filters.command("bulkdelete") & filters.user(ADMINS))
async def bulk_delete_command(client, message):
    """Handle bulk delete command"""
    try:
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if not args:
            await message.reply(
                "⚠️ This command will delete multiple files based on criteria.\n\n"
                "Usage examples:\n"
                "• `/bulkdelete type=movie year=2010` - Delete all movies from 2010\n"
                "• `/bulkdelete quality=camrip` - Delete all CAMRip quality files\n"
                "• `/bulkdelete confirm=true type=movie year=2010` - Delete without confirmation\n\n"
                "⚠️ Add `confirm=true` to skip confirmation."
            )
            return
            
        # Parse arguments
        query = {}
        confirm = False
        
        for arg in args:
            if "=" not in arg:
                continue
                
            key, value = arg.split("=", 1)
            
            if key == "confirm" and value.lower() in ["true", "yes"]:
                confirm = True
            elif key in ["type", "year", "season", "episode", "quality"]:
                query[key] = value
                
        # Check if we have a valid query
        if not query:
            await message.reply("No valid search criteria provided.")
            return
            
        # Count matching files
        count = await bulk_ops.files.count_documents(query)
        
        if count == 0:
            await message.reply("No files match the specified criteria.")
            return
            
        # Confirm deletion
        if not confirm:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Cancel", callback_data="bulk_delete_cancel"),
                    InlineKeyboardButton("Confirm Delete", callback_data=f"bulk_delete_confirm_{json.dumps(query)}")
                ]
            ])
            
            await message.reply(
                f"⚠️ You are about to delete {count} files matching these criteria:\n"
                f"{json.dumps(query, indent=2)}\n\n"
                f"Are you sure you want to continue?",
                reply_markup=keyboard
            )
            return
            
        # Perform deletion
        status_msg = await message.reply(f"Deleting {count} files...")
        
        result = await bulk_ops.files.delete_many(query)
        
        await status_msg.edit(f"Deleted {result.deleted_count} files matching the specified criteria.")
    except Exception as e:
        logger.error(f"Error in bulk delete command: {e}")
        await message.reply(f"Error: {str(e)}")

# Callback handlers
@MainBot.on_callback_query(filters.regex(r"^bulk_delete_"))
async def bulk_delete_callback(client, callback_query):
    """Handle bulk delete confirmation callbacks"""
    try:
        action = callback_query.data.split("_", 3)[2]
        
        if action == "cancel":
            await callback_query.message.edit("Bulk delete operation cancelled.")
        elif action == "confirm":
            # Parse the query
            query_str = callback_query.data.split("_", 3)[3]
            query = json.loads(query_str)
            
            # Update message
            await callback_query.message.edit(f"Deleting files matching criteria... Please wait.")
            
            # Perform deletion
            result = await bulk_ops.files.delete_many(query)
            
            # Update message with results
            await callback_query.message.edit(f"Deleted {result.deleted_count} files matching the specified criteria.")
    except Exception as e:
        logger.error(f"Error in bulk delete callback: {e}")
        await callback_query.answer(f"Error: {str(e)}", show_alert=True) 