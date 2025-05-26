import motor.motor_asyncio
from pymongo.errors import DuplicateKeyError
from database.db_helpers import get_mongo_client, get_async_mongo_client
from info import DATABASE_NAME, OTHER_DB_URI
from datetime import datetime, timedelta
import time

class Analytics:
    def __init__(self):
        self._client = get_async_mongo_client(OTHER_DB_URI)
        self.db = self._client[DATABASE_NAME]
        self.analytics = self.db.user_analytics
        self.file_stats = self.db.file_stats
    
    async def track_activity(self, user_id, activity_type, file_id=None, query=None, extra_data=None):
        """
        Track a user activity in the database
        activity_type: search, file_access, premium_feature_use, etc.
        """
        timestamp = datetime.now()
        
        analytics_data = {
            "user_id": user_id,
            "activity_type": activity_type,
            "timestamp": timestamp,
            "day": timestamp.strftime("%Y-%m-%d"),
            "hour": timestamp.hour
        }
        
        if file_id:
            analytics_data["file_id"] = file_id
        
        if query:
            analytics_data["query"] = query
            
        if extra_data and isinstance(extra_data, dict):
            analytics_data.update(extra_data)
            
        await self.analytics.insert_one(analytics_data)
        
        # Update file statistics if file_id is provided
        if file_id:
            await self.increment_file_stats(file_id, user_id)
    
    async def increment_file_stats(self, file_id, user_id):
        """Increment access count for a file"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Use upsert to create the document if it doesn't exist
        await self.file_stats.update_one(
            {"file_id": file_id},
            {
                "$inc": {
                    "access_count": 1,
                    f"daily_counts.{today}": 1
                },
                "$addToSet": {"accessed_by": user_id}
            },
            upsert=True
        )

    async def get_user_activity(self, user_id, days=7):
        """Get activity statistics for a specific user"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get overall stats
        total_searches = await self.analytics.count_documents({
            "user_id": user_id,
            "activity_type": "search",
            "timestamp": {"$gt": cutoff_date}
        })
        
        total_files_accessed = await self.analytics.count_documents({
            "user_id": user_id,
            "activity_type": "file_access",
            "timestamp": {"$gt": cutoff_date}
        })
        
        premium_features_used = await self.analytics.count_documents({
            "user_id": user_id,
            "activity_type": "premium_feature_use",
            "timestamp": {"$gt": cutoff_date}
        })
        
        # Get daily activity breakdown
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gt": cutoff_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "day": "$day",
                        "activity_type": "$activity_type"
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.day": 1}
            }
        ]
        
        daily_activity = await self.analytics.aggregate(pipeline).to_list(length=100)
        
        # Format daily activity
        activity_by_day = {}
        for item in daily_activity:
            day = item["_id"]["day"]
            activity_type = item["_id"]["activity_type"]
            count = item["count"]
            
            if day not in activity_by_day:
                activity_by_day[day] = {}
                
            activity_by_day[day][activity_type] = count
            
        return {
            "summary": {
                "total_searches": total_searches,
                "files_accessed": total_files_accessed,
                "premium_features_used": premium_features_used
            },
            "daily_activity": activity_by_day
        }

    async def get_most_active_users(self, days=7, limit=10):
        """Get the most active users in the specified time period"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gt": cutoff_date}
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "total_activity": {"$sum": 1},
                    "searches": {
                        "$sum": {
                            "$cond": [{"$eq": ["$activity_type", "search"]}, 1, 0]
                        }
                    },
                    "file_accesses": {
                        "$sum": {
                            "$cond": [{"$eq": ["$activity_type", "file_access"]}, 1, 0]
                        }
                    }
                }
            },
            {
                "$sort": {"total_activity": -1}
            },
            {
                "$limit": limit
            }
        ]
        
        return await self.analytics.aggregate(pipeline).to_list(length=limit)
        
    async def get_most_accessed_files(self, days=7, limit=10):
        """Get the most accessed files in the specified time period"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Query to get files with most accesses
        pipeline = [
            {
                "$match": {
                    "activity_type": "file_access",
                    "timestamp": {"$gt": cutoff_date}
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
                "$limit": limit
            }
        ]
        
        return await self.analytics.aggregate(pipeline).to_list(length=limit)
    
    async def get_popular_search_terms(self, days=7, limit=10):
        """Get the most popular search terms"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "activity_type": "search",
                    "timestamp": {"$gt": cutoff_date},
                    "query": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": "$query",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            },
            {
                "$limit": limit
            }
        ]
        
        return await self.analytics.aggregate(pipeline).to_list(length=limit)
        
    async def get_hourly_usage_stats(self, days=1):
        """Get hourly usage statistics for the last day"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gt": cutoff_date}
                }
            },
            {
                "$group": {
                    "_id": "$hour",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        hourly_stats = await self.analytics.aggregate(pipeline).to_list(length=24)
        
        # Format the results as a list of 24 hours
        result = [0] * 24
        for stat in hourly_stats:
            result[stat["_id"]] = stat["count"]
            
        return result

    async def find_duplicate_files(self, limit=50):
        """Find potential duplicate files based on similar access patterns"""
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$toLower": "$query"
                    },
                    "count": {"$sum": 1},
                    "file_ids": {"$addToSet": "$file_id"}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1},
                    "file_ids.1": {"$exists": True}  # At least 2 file IDs
                }
            },
            {
                "$project": {
                    "query": "$_id",
                    "file_ids": 1,
                    "count": 1
                }
            },
            {
                "$sort": {"count": -1}
            },
            {
                "$limit": limit
            }
        ]
        
        return await self.analytics.aggregate(pipeline).to_list(length=limit)

analytics_db = Analytics() 