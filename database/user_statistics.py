import motor.motor_asyncio
import datetime
from info import DATABASE_NAME, OTHER_DB_URI
from database.db_helpers import get_async_mongo_client

class UserStats:
    """Class to handle user statistics tracking"""
    def __init__(self):
        self._client = get_async_mongo_client(OTHER_DB_URI)
        self.db = self._client[DATABASE_NAME]
        self.stats = self.db.user_statistics
        self.file_stats = self.db.file_statistics

    async def log_search_query(self, user_id, query, results_count, timestamp=None):
        """Log a search query made by a user"""
        if timestamp is None:
            timestamp = datetime.datetime.now()
        
        await self.stats.update_one(
            {'user_id': user_id},
            {'$push': {'search_history': {
                'query': query,
                'results_count': results_count,
                'timestamp': timestamp
            }},
            '$inc': {'total_searches': 1}},
            upsert=True
        )

    async def log_file_request(self, user_id, file_id, file_name, file_size, timestamp=None):
        """Log when a user requests a file"""
        if timestamp is None:
            timestamp = datetime.datetime.now()
        
        # Update user statistics
        await self.stats.update_one(
            {'user_id': user_id},
            {'$push': {'file_requests': {
                'file_id': file_id,
                'file_name': file_name,
                'file_size': file_size,
                'timestamp': timestamp
            }},
            '$inc': {'total_file_requests': 1, 'total_file_size_requested': file_size}},
            upsert=True
        )
        
        # Update file statistics
        await self.file_stats.update_one(
            {'file_id': file_id},
            {'$inc': {'request_count': 1},
             '$push': {'requesters': {
                 'user_id': user_id,
                 'timestamp': timestamp
             }}},
            upsert=True
        )

    async def get_user_stats(self, user_id):
        """Get statistics for a specific user"""
        return await self.stats.find_one({'user_id': user_id})

    async def get_user_search_history(self, user_id, limit=10):
        """Get recent search history for a user"""
        user_data = await self.stats.find_one(
            {'user_id': user_id},
            {'search_history': {'$slice': -limit}}
        )
        return user_data.get('search_history', []) if user_data else []

    async def get_user_file_requests(self, user_id, limit=10):
        """Get recent file requests for a user"""
        user_data = await self.stats.find_one(
            {'user_id': user_id},
            {'file_requests': {'$slice': -limit}}
        )
        return user_data.get('file_requests', []) if user_data else []

    async def get_top_users_by_requests(self, limit=10):
        """Get users with most file requests"""
        pipeline = [
            {'$sort': {'total_file_requests': -1}},
            {'$limit': limit},
            {'$project': {
                'user_id': 1,
                'total_file_requests': 1,
                'total_searches': 1
            }}
        ]
        cursor = self.stats.aggregate(pipeline)
        return [doc async for doc in cursor]

    async def get_top_files(self, limit=10):
        """Get most requested files"""
        pipeline = [
            {'$sort': {'request_count': -1}},
            {'$limit': limit}
        ]
        cursor = self.file_stats.aggregate(pipeline)
        return [doc async for doc in cursor]

    async def get_activity_by_time(self, user_id=None, days=7):
        """Get user activity grouped by day for the last N days"""
        match_stage = {'$match': {
            'timestamp': {'$gte': datetime.datetime.now() - datetime.timedelta(days=days)}
        }}
        
        if user_id is not None:
            match_stage['$match']['user_id'] = user_id

        pipeline = [
            match_stage,
            {'$group': {
                '_id': {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1, '_id.day': 1}}
        ]
        
        cursor = self.stats.aggregate(pipeline)
        return [doc async for doc in cursor]

    async def find_duplicate_files(self, similarity_threshold=0.8):
        """Find potential duplicate files based on name similarity"""
        # This is a simplified implementation - in production you might want
        # a more sophisticated approach like TF-IDF or other similarity metrics
        all_files = []
        cursor = self.file_stats.find({}, {'file_id': 1, 'file_name': 1})
        
        async for doc in cursor:
            if 'file_name' in doc and doc['file_name']:
                all_files.append({
                    'file_id': doc['file_id'],
                    'file_name': doc['file_name'].lower()
                })
        
        # Simple implementation - comparing each file with every other file
        # Not optimal for large collections, but works for demonstration
        duplicates = []
        for i, file1 in enumerate(all_files):
            for file2 in all_files[i+1:]:
                # Simple text comparison - can be enhanced with better algorithms
                if self._similarity(file1['file_name'], file2['file_name']) > similarity_threshold:
                    duplicates.append({
                        'file1': file1,
                        'file2': file2
                    })
        
        return duplicates
    
    def _similarity(self, s1, s2):
        """Calculate similarity between two strings"""
        # This is a very simple similarity measure
        # Can be replaced with better algorithms like Levenshtein distance
        if not s1 or not s2:
            return 0
        
        # Convert to sets of words for a simple Jaccard similarity
        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())
        
        if not words1 or not words2:
            return 0
            
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0

# Create a global instance
user_stats = UserStats() 