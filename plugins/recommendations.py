import logging
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main.bot import MainBot
from database.analytics import analytics_db
from database.tiered_access import tiered_access
from info import ADMINS
from pymongo import DESCENDING

logger = logging.getLogger(__name__)

class ContentRecommender:
    def __init__(self):
        """Initialize the content recommender"""
        self.analytics_db = analytics_db
        self.tiered_access = tiered_access
        
    async def get_popular_content(self, days=7, limit=10):
        """Get most popular content based on access statistics"""
        return await self.analytics_db.get_most_accessed_files(days=days, limit=limit)
        
    async def get_similar_content(self, file_id, limit=10):
        """Get content similar to a specific file"""
        # This is a simple implementation - in a real system, you'd use more sophisticated similarity metrics
        
        # First, get the file details
        file_details = await self.analytics_db.db.files.find_one({"file_id": file_id})
        
        if not file_details:
            return []
            
        # Create a query to find similar files
        query = {}
        
        # Match by type
        if "type" in file_details:
            query["type"] = file_details["type"]
            
        # Match by year (with a range)
        if "year" in file_details:
            try:
                year = int(file_details["year"])
                query["year"] = {"$gte": str(year-2), "$lte": str(year+2)}
            except (ValueError, TypeError):
                pass
                
        # Match by genre if available
        if "genre" in file_details and file_details["genre"]:
            query["genre"] = {"$in": [file_details["genre"]]}
            
        # Exclude the original file
        query["file_id"] = {"$ne": file_id}
        
        # Get similar files
        similar_files = await self.analytics_db.db.files.find(
            query,
            {"file_id": 1, "file_name": 1, "size": 1, "caption": 1, "type": 1}
        ).limit(limit).to_list(length=limit)
        
        return similar_files
        
    async def get_user_recommendations(self, user_id, days=30, limit=10):
        """Get personalized recommendations for a user based on their activity"""
        # Get user's recent activity
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get files the user has accessed
        accessed_files = await self.analytics_db.analytics.find(
            {
                "user_id": user_id,
                "activity_type": "file_access",
                "timestamp": {"$gt": cutoff_date},
                "file_id": {"$exists": True}
            }
        ).to_list(length=100)
        
        if not accessed_files:
            # If no activity, return popular content
            return await self.get_popular_content(limit=limit)
            
        # Extract file IDs and get their details
        file_ids = [file["file_id"] for file in accessed_files]
        
        file_details = await self.analytics_db.db.files.find(
            {"file_id": {"$in": file_ids}}
        ).to_list(length=100)
        
        # Extract types, genres, etc. to build a user profile
        types = {}
        genres = {}
        years = {}
        
        for file in file_details:
            # Count occurrences of each type
            file_type = file.get("type")
            if file_type:
                types[file_type] = types.get(file_type, 0) + 1
                
            # Count occurrences of each genre
            file_genre = file.get("genre")
            if file_genre:
                genres[file_genre] = genres.get(file_genre, 0) + 1
                
            # Count occurrences of each year
            file_year = file.get("year")
            if file_year:
                years[file_year] = years.get(file_year, 0) + 1
                
        # Find the most common type, genre, year
        most_common_type = max(types.items(), key=lambda x: x[1])[0] if types else None
        most_common_genre = max(genres.items(), key=lambda x: x[1])[0] if genres else None
        most_common_year = max(years.items(), key=lambda x: x[1])[0] if years else None
        
        # Build query for recommendations
        query = {}
        
        if most_common_type:
            query["type"] = most_common_type
            
        if most_common_genre:
            query["genre"] = most_common_genre
            
        if most_common_year:
            try:
                year = int(most_common_year)
                query["year"] = {"$gte": str(year-3), "$lte": str(year+3)}
            except (ValueError, TypeError):
                pass
                
        # Exclude files the user has already accessed
        query["file_id"] = {"$nin": file_ids}
        
        # Get recommendations
        recommendations = await self.analytics_db.db.files.find(
            query,
            {"file_id": 1, "file_name": 1, "size": 1, "caption": 1, "type": 1}
        ).limit(limit).to_list(length=limit)
        
        # If not enough recommendations, add some popular content
        if len(recommendations) < limit:
            popular = await self.get_popular_content(limit=limit-len(recommendations))
            
            # Filter out duplicates
            existing_ids = [rec["file_id"] for rec in recommendations]
            for file in popular:
                if file["file_id"] not in existing_ids and file["file_id"] not in file_ids:
                    recommendations.append(file)
                    if len(recommendations) >= limit:
                        break
                        
        return recommendations
        
    async def get_trending_content(self, days=3, limit=10):
        """Get trending content (highest growth in popularity)"""
        # Get current popular content
        current_popular = await self.analytics_db.get_most_accessed_files(days=days, limit=50)
        
        # Get previous period popular content
        previous_cutoff = datetime.now() - timedelta(days=days*2)
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Aggregate previous period stats
        pipeline = [
            {
                "$match": {
                    "activity_type": "file_access",
                    "timestamp": {"$gt": previous_cutoff, "$lt": cutoff_date}
                }
            },
            {
                "$group": {
                    "_id": "$file_id",
                    "access_count": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"}
                }
            },
            {
                "$project": {
                    "file_id": "$_id",
                    "access_count": 1,
                    "unique_user_count": {"$size": "$unique_users"}
                }
            },
            {
                "$sort": {"access_count": -1}
            },
            {
                "$limit": 50
            }
        ]
        
        previous_popular = await self.analytics_db.analytics.aggregate(pipeline).to_list(length=50)
        
        # Create a map of previous counts
        previous_counts = {item["file_id"]: item["access_count"] for item in previous_popular}
        
        # Calculate growth rate
        trending = []
        for item in current_popular:
            file_id = item["file_id"]
            current_count = item["access_count"]
            previous_count = previous_counts.get(file_id, 0)
            
            # Avoid division by zero
            if previous_count == 0:
                previous_count = 1
                
            growth_rate = (current_count - previous_count) / previous_count
            
            trending.append({
                "file_id": file_id,
                "file_name": item.get("file_name", "Unknown"),
                "current_count": current_count,
                "previous_count": previous_count,
                "growth_rate": growth_rate,
                "size": item.get("size", 0)
            })
            
        # Sort by growth rate
        trending.sort(key=lambda x: x["growth_rate"], reverse=True)
        
        # Get file details for the top trending items
        trending_ids = [item["file_id"] for item in trending[:limit]]
        
        trending_details = await self.analytics_db.db.files.find(
            {"file_id": {"$in": trending_ids}},
            {"file_id": 1, "file_name": 1, "size": 1, "caption": 1, "type": 1}
        ).to_list(length=limit)
        
        # Sort details to match the trending order
        id_to_details = {file["file_id"]: file for file in trending_details}
        result = []
        for item in trending[:limit]:
            if item["file_id"] in id_to_details:
                result.append(id_to_details[item["file_id"]])
                
        return result

# Create global instance
recommender = ContentRecommender()

# Command handlers
@MainBot.on_message(filters.command("recommend"))
async def recommend_command(client, message):
    """Handle recommendation command"""
    try:
        user_id = message.from_user.id
        
        # Check if user can use recommendations
        can_use_recommendations = await tiered_access.can_use_feature(user_id, "recommendations")
        
        if not can_use_recommendations and user_id not in ADMINS:
            # User cannot use recommendations
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Upgrade Plan", callback_data="upgrade_plan")]
            ])
            await message.reply(
                "⭐ **Premium Feature**\nPersonalized recommendations are available only for premium users. "
                "Please upgrade your plan to access this feature.",
                reply_markup=keyboard
            )
            return
            
        # Parse arguments
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if not args:
            # Show personalized recommendations
            await message.reply("🔍 Finding personalized recommendations for you...")
            recommendations = await recommender.get_user_recommendations(user_id)
            
            if not recommendations:
                await message.reply("No recommendations found. Try exploring some content first!")
                return
                
            # Format results
            msg = "🎬 **Recommended for You**\n\n"
            
            for i, file in enumerate(recommendations[:10], 1):
                file_name = file.get("file_name", "Unknown")
                file_type = file.get("type", "")
                
                msg += f"{i}. `{file_name}`"
                if file_type:
                    msg += f" ({file_type})"
                msg += "\n"
                
            # Create keyboard with file links
            buttons = []
            for i, file in enumerate(recommendations[:10], 1):
                file_id = file.get("file_id")
                if file_id:
                    buttons.append([InlineKeyboardButton(f"{i}. {file.get('file_name', 'File')}", callback_data=f"get_file_{file_id}")])
                    
            keyboard = InlineKeyboardMarkup(buttons)
            
            await message.reply(msg, reply_markup=keyboard)
        elif args[0] == "popular":
            # Show popular content
            days = 7
            if len(args) > 1:
                try:
                    days = int(args[1])
                except ValueError:
                    pass
                    
            await message.reply(f"🔍 Finding popular content from the last {days} days...")
            popular = await recommender.get_popular_content(days=days)
            
            if not popular:
                await message.reply("No popular content found.")
                return
                
            # Format results
            msg = f"🔥 **Popular Content (Last {days} Days)**\n\n"
            
            for i, file in enumerate(popular[:10], 1):
                file_name = file.get("file_name", "Unknown")
                access_count = file.get("access_count", 0)
                
                msg += f"{i}. `{file_name}` - {access_count} accesses\n"
                
            # Create keyboard with file links
            buttons = []
            for i, file in enumerate(popular[:10], 1):
                file_id = file.get("file_id")
                if file_id:
                    buttons.append([InlineKeyboardButton(f"{i}. {file.get('file_name', 'File')}", callback_data=f"get_file_{file_id}")])
                    
            keyboard = InlineKeyboardMarkup(buttons)
            
            await message.reply(msg, reply_markup=keyboard)
        elif args[0] == "trending":
            # Show trending content
            days = 3
            if len(args) > 1:
                try:
                    days = int(args[1])
                except ValueError:
                    pass
                    
            await message.reply(f"🔍 Finding trending content from the last {days} days...")
            trending = await recommender.get_trending_content(days=days)
            
            if not trending:
                await message.reply("No trending content found.")
                return
                
            # Format results
            msg = f"📈 **Trending Content (Last {days} Days)**\n\n"
            
            for i, file in enumerate(trending[:10], 1):
                file_name = file.get("file_name", "Unknown")
                
                msg += f"{i}. `{file_name}`\n"
                
            # Create keyboard with file links
            buttons = []
            for i, file in enumerate(trending[:10], 1):
                file_id = file.get("file_id")
                if file_id:
                    buttons.append([InlineKeyboardButton(f"{i}. {file.get('file_name', 'File')}", callback_data=f"get_file_{file_id}")])
                    
            keyboard = InlineKeyboardMarkup(buttons)
            
            await message.reply(msg, reply_markup=keyboard)
        elif args[0] == "similar" and len(args) > 1:
            # Show similar content
            file_id = args[1]
            
            await message.reply(f"🔍 Finding similar content...")
            similar = await recommender.get_similar_content(file_id)
            
            if not similar:
                await message.reply("No similar content found.")
                return
                
            # Format results
            msg = "🎬 **Similar Content**\n\n"
            
            for i, file in enumerate(similar[:10], 1):
                file_name = file.get("file_name", "Unknown")
                file_type = file.get("type", "")
                
                msg += f"{i}. `{file_name}`"
                if file_type:
                    msg += f" ({file_type})"
                msg += "\n"
                
            # Create keyboard with file links
            buttons = []
            for i, file in enumerate(similar[:10], 1):
                file_id = file.get("file_id")
                if file_id:
                    buttons.append([InlineKeyboardButton(f"{i}. {file.get('file_name', 'File')}", callback_data=f"get_file_{file_id}")])
                    
            keyboard = InlineKeyboardMarkup(buttons)
            
            await message.reply(msg, reply_markup=keyboard)
        else:
            # Show help
            msg = "**Recommendation Commands**\n\n"
            msg += "/recommend - Get personalized recommendations\n"
            msg += "/recommend popular [days] - Get popular content\n"
            msg += "/recommend trending [days] - Get trending content\n"
            msg += "/recommend similar [file_id] - Get content similar to a specific file\n"
            
            await message.reply(msg)
    except Exception as e:
        logger.error(f"Error in recommend command: {e}")
        await message.reply(f"An error occurred: {str(e)}")

# Callback handler for file selection
@MainBot.on_callback_query(filters.regex(r"^rec_file_(.+)"))
async def recommend_file_callback(client, callback_query):
    """Handle file selection from recommendations"""
    try:
        file_id = callback_query.data.split("_", 2)[2]
        
        # Here you would implement the logic to send the file to the user
        # This depends on how your bot handles file sending
        
        await callback_query.answer("Processing your request...")
        
        # Track this recommendation click in analytics
        user_id = callback_query.from_user.id
        await analytics_db.track_activity(
            user_id, 
            "recommendation_click", 
            file_id=file_id,
            extra_data={"source": "recommendation"}
        )
        
        # This is a placeholder - you would need to implement file sending
        await callback_query.message.reply(f"You selected file with ID: {file_id}")
        
    except Exception as e:
        logger.error(f"Error in recommend file callback: {e}")
        await callback_query.answer(f"Error: {str(e)}", show_alert=True) 