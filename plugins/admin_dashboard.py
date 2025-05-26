import logging
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS, DATABASE_NAME
from database.users_chats_db import db
from database.analytics import analytics_db
from database.tiered_access import tiered_access
from main.duplicate_detector import duplicate_detector
from main.nlp_search import nlp_search
from main.bot import MainBot

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

# Admin authentication middleware
@web.middleware
async def admin_auth_middleware(request, handler):
    # Simple auth for now - we'll use a token in the query string
    # In production, you'd want to use a proper auth system
    token = request.query.get('admin_token')
    if not token or token != 'admin_secret_token':  # Replace with a secure token or auth system
        return web.json_response({"error": "Unauthorized"}, status=401)
    return await handler(request)

# Dashboard routes
@routes.get('/admin/dashboard', name='admin_dashboard')
async def admin_dashboard(request):
    """Main admin dashboard page"""
    try:
        # Get basic stats
        user_count = await db.total_users_count()
        chat_count = await db.total_chat_count()
        
        # Get active users in last 7 days
        active_users = await analytics_db.get_most_active_users(days=7, limit=10)
        
        # Get popular files
        popular_files = await analytics_db.get_most_accessed_files(days=7, limit=10)
        
        # Get popular search terms
        popular_searches = await analytics_db.get_popular_search_terms(days=7, limit=10)
        
        # Get hourly usage stats
        hourly_stats = await analytics_db.get_hourly_usage_stats(days=1)
        
        # Get tier stats
        tier_stats = await tiered_access.get_tier_stats()
        
        return web.json_response({
            "stats": {
                "total_users": user_count,
                "total_chats": chat_count,
                "active_users": len(active_users)
            },
            "active_users": active_users,
            "popular_files": popular_files,
            "popular_searches": popular_searches,
            "hourly_stats": hourly_stats,
            "tier_stats": tier_stats
        })
    except Exception as e:
        logger.error(f"Error in admin dashboard: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.get('/admin/users', name='admin_users')
async def admin_users(request):
    """Get user list with pagination"""
    try:
        page = int(request.query.get('page', 1))
        limit = int(request.query.get('limit', 50))
        skip = (page - 1) * limit
        
        # Get users with pagination
        users_cursor = db.col.find().skip(skip).limit(limit)
        users = await users_cursor.to_list(length=limit)
        
        # Format user data
        formatted_users = []
        for user in users:
            formatted_users.append({
                "id": user.get("id"),
                "name": user.get("name"),
                "ban_status": user.get("ban_status"),
                "tier": await tiered_access.get_user_tier(user.get("id"))
            })
        
        # Get total count for pagination
        total_users = await db.total_users_count()
        total_pages = (total_users + limit - 1) // limit
        
        return web.json_response({
            "users": formatted_users,
            "pagination": {
                "total": total_users,
                "page": page,
                "limit": limit,
                "pages": total_pages
            }
        })
    except Exception as e:
        logger.error(f"Error in admin users: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.get('/admin/user/{user_id}', name='admin_user_detail')
async def admin_user_detail(request):
    """Get detailed information about a specific user"""
    try:
        user_id = int(request.match_info['user_id'])
        
        # Get user details
        user = await db.get_user(user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)
        
        # Get user tier
        tier = await tiered_access.get_user_tier(user_id)
        
        # Get user activity
        activity = await analytics_db.get_user_activity(user_id, days=30)
        
        return web.json_response({
            "user": user,
            "tier": tier,
            "activity": activity
        })
    except Exception as e:
        logger.error(f"Error in user detail: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post('/admin/user/{user_id}/ban', name='admin_ban_user')
async def admin_ban_user(request):
    """Ban a user"""
    try:
        user_id = int(request.match_info['user_id'])
        data = await request.json()
        reason = data.get('reason', 'No reason provided')
        
        await db.ban_user(user_id, reason)
        
        return web.json_response({"success": True, "message": f"User {user_id} has been banned"})
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post('/admin/user/{user_id}/unban', name='admin_unban_user')
async def admin_unban_user(request):
    """Unban a user"""
    try:
        user_id = int(request.match_info['user_id'])
        
        await db.remove_ban(user_id)
        
        return web.json_response({"success": True, "message": f"User {user_id} has been unbanned"})
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post('/admin/user/{user_id}/tier', name='admin_set_user_tier')
async def admin_set_user_tier(request):
    """Set a user's tier"""
    try:
        user_id = int(request.match_info['user_id'])
        data = await request.json()
        tier_name = data.get('tier_name')
        duration_days = int(data.get('duration_days', 30))
        
        success, message = await tiered_access.set_user_tier(user_id, tier_name, duration_days)
        
        if success:
            return web.json_response({"success": True, "message": message})
        else:
            return web.json_response({"error": message}, status=400)
    except Exception as e:
        logger.error(f"Error setting user tier: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.get('/admin/tiers', name='admin_tiers')
async def admin_tiers(request):
    """Get all tier configurations"""
    try:
        tiers = await tiered_access.get_all_tiers()
        return web.json_response({"tiers": tiers})
    except Exception as e:
        logger.error(f"Error getting tiers: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post('/admin/tiers/{tier_name}', name='admin_update_tier')
async def admin_update_tier(request):
    """Update a tier configuration"""
    try:
        tier_name = request.match_info['tier_name']
        data = await request.json()
        
        await tiered_access.update_tier_config(tier_name, data)
        
        return web.json_response({"success": True, "message": f"Tier {tier_name} has been updated"})
    except Exception as e:
        logger.error(f"Error updating tier: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.get('/admin/duplicates', name='admin_duplicates')
async def admin_duplicates(request):
    """Get duplicate files"""
    try:
        status = request.query.get('status', 'unresolved')
        limit = int(request.query.get('limit', 50))
        
        duplicates = await duplicate_detector.get_all_duplicates(status=status, limit=limit)
        
        return web.json_response({"duplicates": duplicates})
    except Exception as e:
        logger.error(f"Error getting duplicates: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post('/admin/duplicates/find', name='admin_find_duplicates')
async def admin_find_duplicates(request):
    """Find duplicate files using different methods"""
    try:
        data = await request.json()
        method = data.get('method', 'filename')
        limit = int(data.get('limit', 50))
        
        if method == 'filename':
            min_similarity = float(data.get('min_similarity', 0.85))
            duplicates = await duplicate_detector.find_by_filename_similarity(min_similarity=min_similarity, limit=limit)
        elif method == 'size':
            duplicates = await duplicate_detector.find_by_size_match(limit=limit)
        elif method == 'content':
            duplicates = await duplicate_detector.find_by_content_type(limit=limit)
        else:
            return web.json_response({"error": "Invalid method"}, status=400)
        
        return web.json_response({
            "success": True, 
            "duplicates_found": len(duplicates),
            "duplicates": duplicates
        })
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post('/admin/duplicates/{duplicate_id}/resolve', name='admin_resolve_duplicate')
async def admin_resolve_duplicate(request):
    """Mark a duplicate as resolved"""
    try:
        duplicate_id = request.match_info['duplicate_id']
        
        await duplicate_detector.mark_as_resolved(duplicate_id)
        
        return web.json_response({"success": True, "message": "Duplicate marked as resolved"})
    except Exception as e:
        logger.error(f"Error resolving duplicate: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.delete('/admin/duplicates/file/{file_id}', name='admin_delete_duplicate')
async def admin_delete_duplicate(request):
    """Delete a duplicate file"""
    try:
        file_id = request.match_info['file_id']
        
        await duplicate_detector.delete_duplicate(file_id)
        
        return web.json_response({"success": True, "message": f"File {file_id} marked as deleted"})
    except Exception as e:
        logger.error(f"Error deleting duplicate: {e}")
        return web.json_response({"error": str(e)}, status=500)

# Telegram command handlers for admin dashboard
@MainBot.on_message(filters.command("analytics") & filters.user(ADMINS))
async def analytics_command(client, message):
    """Show analytics summary"""
    try:
        # Get basic stats
        user_count = await db.total_users_count()
        chat_count = await db.total_chat_count()
        
        # Get active users in last 7 days
        active_users = await analytics_db.get_most_active_users(days=7, limit=5)
        
        # Get popular files
        popular_files = await analytics_db.get_most_accessed_files(days=7, limit=5)
        
        # Format message
        msg = f"📊 **Analytics Summary**\n\n"
        msg += f"👥 Total Users: {user_count}\n"
        msg += f"💬 Total Chats: {chat_count}\n\n"
        
        msg += "**Most Active Users (7 days)**\n"
        for i, user in enumerate(active_users, 1):
            msg += f"{i}. User ID: {user['_id']} - {user['total_activity']} activities\n"
        
        msg += "\n**Most Accessed Files (7 days)**\n"
        for i, file in enumerate(popular_files, 1):
            msg += f"{i}. File ID: {file['file_id']} - {file['access_count']} accesses\n"
            
        # Create keyboard for more options
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("User Stats", callback_data="admin_stats_users"),
                InlineKeyboardButton("File Stats", callback_data="admin_stats_files")
            ],
            [
                InlineKeyboardButton("Search Stats", callback_data="admin_stats_search"),
                InlineKeyboardButton("Tier Stats", callback_data="admin_stats_tiers")
            ]
        ])
        
        await message.reply(msg, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in analytics command: {e}")
        await message.reply(f"Error: {str(e)}")

@MainBot.on_message(filters.command("duplicates") & filters.user(ADMINS))
async def duplicates_command(client, message):
    """Show duplicate files"""
    try:
        # Parse arguments
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if args and args[0] == "find":
            method = args[1] if len(args) > 1 else "filename"
            
            # Send initial message
            status_msg = await message.reply(f"🔍 Finding duplicates using {method} method... This may take some time.")
            
            # Find duplicates based on method
            if method == "filename":
                duplicates = await duplicate_detector.find_by_filename_similarity(limit=20)
            elif method == "size":
                duplicates = await duplicate_detector.find_by_size_match(limit=20)
            elif method == "content":
                duplicates = await duplicate_detector.find_by_content_type(limit=20)
            else:
                await status_msg.edit(f"❌ Invalid method: {method}")
                return
                
            # Format results
            if duplicates:
                msg = f"🔍 Found {len(duplicates)} potential duplicate groups:\n\n"
                for i, dup in enumerate(duplicates[:5], 1):
                    msg += f"Group {i}:\n"
                    msg += f"• Original: {dup['original']['file_name']}\n"
                    msg += f"• {len(dup['duplicates'])} duplicates\n\n"
                
                if len(duplicates) > 5:
                    msg += f"...and {len(duplicates) - 5} more groups."
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("View All Duplicates", callback_data="admin_view_duplicates")]
                ])
                
                await status_msg.edit(msg, reply_markup=keyboard)
            else:
                await status_msg.edit("✅ No duplicates found.")
        else:
            # Show existing duplicates
            duplicates = await duplicate_detector.get_all_duplicates(limit=10)
            
            if duplicates:
                msg = f"🔍 Found {len(duplicates)} duplicate groups:\n\n"
                for i, dup in enumerate(duplicates[:5], 1):
                    msg += f"Group {i}:\n"
                    msg += f"• Original: {dup['original']['file_name']}\n"
                    msg += f"• {len(dup['duplicates'])} duplicates\n\n"
                
                if len(duplicates) > 5:
                    msg += f"...and {len(duplicates) - 5} more groups."
                
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Find More", callback_data="admin_find_duplicates"),
                        InlineKeyboardButton("View All", callback_data="admin_view_duplicates")
                    ]
                ])
                
                await message.reply(msg, reply_markup=keyboard)
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Find Duplicates", callback_data="admin_find_duplicates")]
                ])
                await message.reply("No duplicates found in the database.", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in duplicates command: {e}")
        await message.reply(f"Error: {str(e)}")

@MainBot.on_message(filters.command("tiers") & filters.user(ADMINS))
async def tiers_command(client, message):
    """Manage user tiers"""
    try:
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if not args:
            # Show tier stats
            tier_stats = await tiered_access.get_tier_stats()
            
            msg = "📊 **User Tier Statistics**\n\n"
            for tier in tier_stats:
                msg += f"**{tier['_id']}**: {tier['count']} users\n"
                
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("View Tier Configs", callback_data="admin_view_tiers")]
            ])
            
            await message.reply(msg, reply_markup=keyboard)
        elif args[0] == "set" and len(args) >= 3:
            # Set a user's tier
            try:
                user_id = int(args[1])
                tier_name = args[2]
                duration = int(args[3]) if len(args) > 3 else 30
                
                success, msg = await tiered_access.set_user_tier(user_id, tier_name, duration)
                
                if success:
                    await message.reply(f"✅ {msg}")
                else:
                    await message.reply(f"❌ {msg}")
            except ValueError:
                await message.reply("❌ Invalid user ID or duration. Please use integers.")
        elif args[0] == "config":
            # Show tier configurations
            tiers = await tiered_access.get_all_tiers()
            
            msg = "⚙️ **Tier Configurations**\n\n"
            for tier in tiers:
                msg += f"**{tier['tier_name']}**: {tier['description']}\n"
                msg += f"• Max requests: {tier['max_requests_per_day'] or 'Unlimited'}\n"
                msg += f"• Max file size: {tier['max_file_size'] or 'Unlimited'} MB\n\n"
                
            await message.reply(msg)
        else:
            # Show help
            msg = "**Tier Management Commands**\n\n"
            msg += "/tiers - Show tier statistics\n"
            msg += "/tiers set [user_id] [tier_name] [duration_days] - Set a user's tier\n"
            msg += "/tiers config - Show tier configurations\n"
            
            await message.reply(msg)
    except Exception as e:
        logger.error(f"Error in tiers command: {e}")
        await message.reply(f"Error: {str(e)}")

# Add the admin dashboard routes to the main web app
def setup_admin_routes(app):
    # Apply admin auth middleware only to admin routes
    admin_app = web.Application(middlewares=[admin_auth_middleware])
    admin_app.add_routes(routes)
    app.add_subapp('/admin/', admin_app)
    return app 