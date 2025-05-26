import motor.motor_asyncio
import datetime
from info import DATABASE_NAME, OTHER_DB_URI
from database.db_helpers import get_async_mongo_client

# Define the tiers with their features
# This can be customized as needed
DEFAULT_TIERS = {
    "free": {
        "name": "Free",
        "description": "Basic access",
        "features": {
            "requests_per_day": 25,
            "shortlink_required": True,
            "verification_required": True,
            "direct_files": False,
            "ad_free": False,
            "high_speed": False,
            "multi_player": False
        }
    },
    "basic": {
        "name": "Basic",
        "description": "Entry-level premium access",
        "features": {
            "requests_per_day": 75,
            "shortlink_required": False,
            "verification_required": True,
            "direct_files": True,
            "ad_free": False,
            "high_speed": False,
            "multi_player": False
        }
    },
    "standard": {
        "name": "Standard",
        "description": "Standard premium access",
        "features": {
            "requests_per_day": 150,
            "shortlink_required": False,
            "verification_required": False,
            "direct_files": True,
            "ad_free": True,
            "high_speed": True,
            "multi_player": False
        }
    },
    "premium": {
        "name": "Premium",
        "description": "Full premium access",
        "features": {
            "requests_per_day": -1,  # Unlimited
            "shortlink_required": False,
            "verification_required": False,
            "direct_files": True,
            "ad_free": True,
            "high_speed": True,
            "multi_player": True
        }
    }
}

class TieredAccess:
    """Class to handle tiered access control"""
    def __init__(self):
        self._client = get_async_mongo_client(OTHER_DB_URI)
        self.db = self._client[DATABASE_NAME]
        self.users = self.db.users  # Reuse the existing users collection
        self.tiers = self.db.tiers
        
        # Initialize default tiers if they don't exist
        self._init_default_tiers()
        
    async def _init_default_tiers(self):
        """Initialize the default tiers in the database"""
        for tier_id, tier_data in DEFAULT_TIERS.items():
            await self.tiers.update_one(
                {'tier_id': tier_id},
                {'$set': tier_data},
                upsert=True
            )
    
    async def get_all_tiers(self):
        """Get all available tiers"""
        cursor = self.tiers.find()
        return [doc async for doc in cursor]
    
    async def get_tier(self, tier_id):
        """Get a specific tier by ID"""
        return await self.tiers.find_one({'tier_id': tier_id})
    
    async def get_tier_features(self, tier_id):
        """Get features for a specific tier"""
        tier = await self.get_tier(tier_id)
        return tier.get('features', {}) if tier else {}
    
    async def update_tier(self, tier_id, tier_data):
        """Update a tier's configuration"""
        await self.tiers.update_one(
            {'tier_id': tier_id},
            {'$set': tier_data},
            upsert=True
        )
    
    async def create_tier(self, tier_id, tier_data):
        """Create a new tier"""
        await self.tiers.insert_one({
            'tier_id': tier_id,
            **tier_data
        })
    
    async def delete_tier(self, tier_id):
        """Delete a tier"""
        # Don't allow deletion of default tiers
        if tier_id in DEFAULT_TIERS:
            return False
        
        result = await self.tiers.delete_one({'tier_id': tier_id})
        return result.deleted_count > 0
    
    async def get_user_tier(self, user_id):
        """Get a user's current tier"""
        user = await self.users.find_one({'id': int(user_id)})
        
        # If user doesn't exist or has no tier, return 'free'
        if not user or 'tier' not in user:
            return 'free'
        
        # Check if premium access has expired
        if user.get('expiry_time') and isinstance(user['expiry_time'], datetime.datetime):
            if datetime.datetime.now() > user['expiry_time']:
                # Premium expired, revert to free
                await self.users.update_one(
                    {'id': int(user_id)}, 
                    {'$set': {'tier': 'free', 'expiry_time': None}}
                )
                return 'free'
        
        return user.get('tier', 'free')
    
    async def set_user_tier(self, user_id, tier_id, duration=None):
        """
        Set a user's tier
        
        Args:
            user_id: The user ID
            tier_id: The tier ID to set
            duration: Duration in seconds, or None for permanent
        """
        # Calculate expiry time if duration is provided
        expiry_time = None
        if duration:
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
        
        # Update user's tier
        await self.users.update_one(
            {'id': int(user_id)},
            {'$set': {
                'tier': tier_id,
                'expiry_time': expiry_time
            }},
            upsert=True
        )
        
        return True
    
    async def can_use_feature(self, user_id, feature):
        """Check if a user can use a specific feature"""
        tier_id = await self.get_user_tier(user_id)
        tier_features = await self.get_tier_features(tier_id)
        
        return tier_features.get(feature, False)
    
    async def check_request_limit(self, user_id):
        """
        Check if user has reached their daily request limit
        
        Returns:
            (bool, int): (can_make_request, remaining_requests)
        """
        tier_id = await self.get_user_tier(user_id)
        tier_features = await self.get_tier_features(tier_id)
        
        # Get daily request limit
        daily_limit = tier_features.get('requests_per_day', 0)
        
        # If unlimited (-1), always allow
        if daily_limit == -1:
            return True, -1
        
        # Get today's date
        today = datetime.datetime.now().date()
        today_start = datetime.datetime.combine(today, datetime.time.min)
        
        # Get requests made today
        user = await self.users.find_one({'id': int(user_id)})
        requests_today = 0
        
        if user and 'daily_requests' in user:
            # Check if the stored date is today
            if user['daily_requests'].get('date') == today.isoformat():
                requests_today = user['daily_requests'].get('count', 0)
            else:
                # Reset counter for the new day
                await self.users.update_one(
                    {'id': int(user_id)},
                    {'$set': {'daily_requests': {'date': today.isoformat(), 'count': 0}}}
                )
        
        # Check if limit exceeded
        remaining = daily_limit - requests_today
        can_request = remaining > 0
        
        return can_request, remaining
    
    async def increment_request_count(self, user_id):
        """Increment the user's request count for today"""
        today = datetime.datetime.now().date()
        
        # Increment the counter
        await self.users.update_one(
            {'id': int(user_id)},
            {'$inc': {'daily_requests.count': 1},
             '$set': {'daily_requests.date': today.isoformat()}},
            upsert=True
        )

# Create a global instance
tiered_access = TieredAccess() 