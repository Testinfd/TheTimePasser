import motor.motor_asyncio
from pymongo.errors import DuplicateKeyError
from database.db_helpers import get_mongo_client, get_async_mongo_client
from info import DATABASE_NAME, OTHER_DB_URI
from datetime import datetime, timedelta
import time

class TieredAccess:
    """
    Handle tiered access levels for users
    Tiers:
    - free: Basic access with limited features
    - premium: Standard premium access
    - pro: Advanced premium access with more features
    - enterprise: Full access with unlimited features
    """
    
    def __init__(self):
        self._client = get_async_mongo_client(OTHER_DB_URI)
        self.db = self._client[DATABASE_NAME]
        self.tiers = self.db.user_tiers
        self.tier_config = self.db.tier_config
        
    async def initialize(self):
        """Initialize default tier configurations if they don't exist"""
        default_tiers = [
            {
                "tier_name": "free",
                "description": "Basic access with limited features",
                "max_requests_per_day": 50,
                "max_file_size": 100,  # in MB
                "features": {
                    "can_download": True,
                    "can_stream": True,
                    "batch_requests": False,
                    "remove_ads": False,
                    "early_access": False,
                    "priority_support": False
                },
                "referral_bonus": 0
            },
            {
                "tier_name": "premium",
                "description": "Standard premium access",
                "max_requests_per_day": 200,
                "max_file_size": 500,  # in MB
                "features": {
                    "can_download": True,
                    "can_stream": True,
                    "batch_requests": True,
                    "remove_ads": True,
                    "early_access": False,
                    "priority_support": False
                },
                "referral_bonus": 1
            },
            {
                "tier_name": "pro",
                "description": "Advanced premium access with more features",
                "max_requests_per_day": 500,
                "max_file_size": 1000,  # in MB
                "features": {
                    "can_download": True,
                    "can_stream": True,
                    "batch_requests": True,
                    "remove_ads": True,
                    "early_access": True,
                    "priority_support": False
                },
                "referral_bonus": 2
            },
            {
                "tier_name": "enterprise",
                "description": "Full access with unlimited features",
                "max_requests_per_day": 0,  # unlimited
                "max_file_size": 0,  # unlimited
                "features": {
                    "can_download": True,
                    "can_stream": True,
                    "batch_requests": True,
                    "remove_ads": True,
                    "early_access": True,
                    "priority_support": True
                },
                "referral_bonus": 3
            }
        ]
        
        # Insert default tiers if they don't exist
        for tier in default_tiers:
            await self.tier_config.update_one(
                {"tier_name": tier["tier_name"]},
                {"$set": tier},
                upsert=True
            )
    
    async def get_user_tier(self, user_id):
        """Get the current tier for a user"""
        user_tier = await self.tiers.find_one({"user_id": user_id})
        
        if not user_tier:
            # Default to free tier
            return {
                "user_id": user_id,
                "tier": "free",
                "expiry": None,
                "usage": {
                    "requests_today": 0,
                    "last_request_date": None
                },
                "features_override": {}  # Custom overrides for specific features
            }
            
        # Reset request count if it's a new day
        if user_tier.get("usage", {}).get("last_request_date") != datetime.now().strftime("%Y-%m-%d"):
            user_tier["usage"]["requests_today"] = 0
            user_tier["usage"]["last_request_date"] = datetime.now().strftime("%Y-%m-%d")
            await self.tiers.update_one(
                {"user_id": user_id},
                {"$set": {
                    "usage.requests_today": 0,
                    "usage.last_request_date": datetime.now().strftime("%Y-%m-%d")
                }}
            )
            
        return user_tier
    
    async def set_user_tier(self, user_id, tier_name, duration_days=30):
        """Set a user's tier with an expiry date"""
        # Check if the tier exists
        tier_exists = await self.tier_config.find_one({"tier_name": tier_name})
        if not tier_exists:
            return False, f"Tier '{tier_name}' does not exist"
        
        # Calculate expiry date
        expiry = datetime.now() + timedelta(days=duration_days) if duration_days > 0 else None
        
        # Set or update the user's tier
        await self.tiers.update_one(
            {"user_id": user_id},
            {"$set": {
                "tier": tier_name,
                "expiry": expiry,
                "updated_at": datetime.now()
            }},
            upsert=True
        )
        
        return True, f"User {user_id} has been assigned to tier '{tier_name}' for {duration_days} days"
    
    async def increment_usage(self, user_id):
        """Increment the usage count for a user and check if they've reached their limit"""
        user_tier = await self.get_user_tier(user_id)
        tier_config = await self.tier_config.find_one({"tier_name": user_tier["tier"]})
        
        # Check if user's tier has expired
        if user_tier.get("expiry") and user_tier["expiry"] < datetime.now():
            # Reset to free tier
            await self.tiers.update_one(
                {"user_id": user_id},
                {"$set": {
                    "tier": "free",
                    "expiry": None,
                    "updated_at": datetime.now()
                }}
            )
            user_tier["tier"] = "free"
            tier_config = await self.tier_config.find_one({"tier_name": "free"})
        
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Reset counter if it's a new day
        if user_tier.get("usage", {}).get("last_request_date") != today:
            await self.tiers.update_one(
                {"user_id": user_id},
                {"$set": {
                    "usage.requests_today": 1,
                    "usage.last_request_date": today
                }}
            )
            return True
        
        # Increment the counter
        new_count = user_tier.get("usage", {}).get("requests_today", 0) + 1
        await self.tiers.update_one(
            {"user_id": user_id},
            {"$set": {"usage.requests_today": new_count}}
        )
        
        # Check if user has reached their limit
        max_requests = tier_config.get("max_requests_per_day", 0)
        if max_requests > 0 and new_count > max_requests:
            return False
            
        return True
    
    async def can_use_feature(self, user_id, feature_name):
        """Check if a user can use a specific feature based on their tier"""
        user_tier = await self.get_user_tier(user_id)
        tier_config = await self.tier_config.find_one({"tier_name": user_tier["tier"]})
        
        # Check for feature override first
        if user_tier.get("features_override", {}).get(feature_name) is not None:
            return user_tier["features_override"][feature_name]
        
        # Then check the tier's default settings
        return tier_config.get("features", {}).get(feature_name, False)
    
    async def override_feature(self, user_id, feature_name, allowed):
        """Override a specific feature for a user"""
        await self.tiers.update_one(
            {"user_id": user_id},
            {"$set": {f"features_override.{feature_name}": allowed}}
        )
        
    async def get_all_tiers(self):
        """Get all tier configurations"""
        return await self.tier_config.find().to_list(length=100)
    
    async def update_tier_config(self, tier_name, config_data):
        """Update a tier's configuration"""
        return await self.tier_config.update_one(
            {"tier_name": tier_name}, 
            {"$set": config_data}
        )
    
    async def get_users_by_tier(self, tier_name):
        """Get all users in a specific tier"""
        return await self.tiers.find({"tier": tier_name}).to_list(length=1000)
    
    async def get_tier_stats(self):
        """Get statistics about tiers"""
        pipeline = [
            {
                "$group": {
                    "_id": "$tier",
                    "count": {"$sum": 1},
                    "users": {"$push": "$user_id"}
                }
            }
        ]
        
        return await self.tiers.aggregate(pipeline).to_list(length=100)

tiered_access = TieredAccess() 