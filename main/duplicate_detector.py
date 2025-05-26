import logging
import asyncio
import difflib
from datetime import datetime
from database.db_helpers import get_mongo_client, get_async_mongo_client
from info import DATABASE_NAME, OTHER_DB_URI

logger = logging.getLogger(__name__)

class DuplicateDetector:
    def __init__(self):
        """Initialize the duplicate detector with MongoDB connection"""
        self._client = get_async_mongo_client(OTHER_DB_URI)
        self.db = self._client[DATABASE_NAME]
        self.files = self.db.files
        self.duplicates = self.db.detected_duplicates
        
    async def find_by_filename_similarity(self, min_similarity=0.85, limit=50):
        """Find duplicate files based on filename similarity"""
        try:
            # Get all files
            files = await self.files.find({}, {"file_id": 1, "file_name": 1, "size": 1}).to_list(length=None)
            
            # Group by similar filenames
            duplicates = []
            processed_ids = set()
            
            # Compare each file with others
            for i, file in enumerate(files):
                if file["file_id"] in processed_ids:
                    continue
                    
                file_name = file.get("file_name", "").lower()
                if not file_name:
                    continue
                
                similar_files = []
                
                # Compare with other files
                for other in files[i+1:]:
                    other_name = other.get("file_name", "").lower()
                    if not other_name:
                        continue
                        
                    # Calculate similarity using difflib
                    similarity = difflib.SequenceMatcher(None, file_name, other_name).ratio()
                    
                    if similarity >= min_similarity:
                        similar_files.append({
                            "file_id": other["file_id"],
                            "file_name": other.get("file_name", ""),
                            "size": other.get("size", 0),
                            "similarity": similarity
                        })
                        processed_ids.add(other["file_id"])
                
                if similar_files:
                    # Add to duplicates list
                    duplicates.append({
                        "original": {
                            "file_id": file["file_id"],
                            "file_name": file.get("file_name", ""),
                            "size": file.get("size", 0)
                        },
                        "duplicates": similar_files,
                        "method": "filename_similarity",
                        "duplicate_id": f"sim_{file['file_id']}",
                        "detected_at": datetime.now(),
                        "status": "unresolved"
                    })
                    
                    # Save to database
                    await self.duplicates.update_one(
                        {"duplicate_id": f"sim_{file['file_id']}"},
                        {"$set": duplicates[-1]},
                        upsert=True
                    )
                    
                # Limit results
                if len(duplicates) >= limit:
                    break
                    
            return duplicates
        except Exception as e:
            logger.error(f"Error finding duplicates by filename: {e}")
            return []
    
    async def find_by_size_match(self, limit=50):
        """Find duplicate files based on identical size"""
        try:
            # Find files with same size
            pipeline = [
                {
                    "$match": {
                        "size": {"$exists": True, "$ne": None, "$gt": 0}
                    }
                },
                {
                    "$group": {
                        "_id": "$size",
                        "count": {"$sum": 1},
                        "files": {"$push": {"file_id": "$file_id", "file_name": "$file_name", "size": "$size"}}
                    }
                },
                {
                    "$match": {
                        "count": {"$gt": 1}
                    }
                },
                {
                    "$sort": {"count": -1}
                },
                {
                    "$limit": limit
                }
            ]
            
            result = await self.files.aggregate(pipeline).to_list(length=limit)
            
            # Format results
            duplicates = []
            for item in result:
                size = item["_id"]
                files = item["files"]
                
                if len(files) <= 1:
                    continue
                    
                original = files[0]
                duplicate_id = f"size_{original['file_id']}"
                
                duplicates.append({
                    "original": original,
                    "duplicates": files[1:],
                    "method": "size_match",
                    "duplicate_id": duplicate_id,
                    "detected_at": datetime.now(),
                    "status": "unresolved"
                })
                
                # Save to database
                await self.duplicates.update_one(
                    {"duplicate_id": duplicate_id},
                    {"$set": duplicates[-1]},
                    upsert=True
                )
                
            return duplicates
        except Exception as e:
            logger.error(f"Error finding duplicates by size: {e}")
            return []
            
    async def find_by_content_type(self, limit=50):
        """Find duplicate files based on content type, naming patterns, etc."""
        try:
            # Find files with similar content types and patterns
            pipeline = [
                {
                    "$match": {
                        "type": {"$exists": True},
                        "year": {"$exists": True}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "type": "$type",
                            "year": "$year"
                        },
                        "count": {"$sum": 1},
                        "files": {"$push": {
                            "file_id": "$file_id",
                            "file_name": "$file_name",
                            "size": "$size",
                            "type": "$type",
                            "year": "$year"
                        }}
                    }
                },
                {
                    "$match": {
                        "count": {"$gt": 1}
                    }
                },
                {
                    "$sort": {"count": -1}
                },
                {
                    "$limit": limit
                }
            ]
            
            result = await self.files.aggregate(pipeline).to_list(length=limit)
            
            # Format results
            duplicates = []
            for item in result:
                content_type = item["_id"]
                files = item["files"]
                
                if len(files) <= 1:
                    continue
                    
                # Sort by size (descending)
                files.sort(key=lambda x: x.get("size", 0), reverse=True)
                
                original = files[0]
                duplicate_id = f"content_{original['file_id']}"
                
                duplicates.append({
                    "original": original,
                    "duplicates": files[1:],
                    "method": "content_type",
                    "duplicate_id": duplicate_id,
                    "detected_at": datetime.now(),
                    "status": "unresolved",
                    "content_info": content_type
                })
                
                # Save to database
                await self.duplicates.update_one(
                    {"duplicate_id": duplicate_id},
                    {"$set": duplicates[-1]},
                    upsert=True
                )
                
            return duplicates
        except Exception as e:
            logger.error(f"Error finding duplicates by content: {e}")
            return []
    
    async def get_all_duplicates(self, status="unresolved", limit=50):
        """Get all detected duplicates with specified status"""
        try:
            return await self.duplicates.find({"status": status}).limit(limit).to_list(length=limit)
        except Exception as e:
            logger.error(f"Error getting duplicates: {e}")
            return []
    
    async def mark_as_resolved(self, duplicate_id):
        """Mark a duplicate as resolved"""
        try:
            await self.duplicates.update_one(
                {"duplicate_id": duplicate_id},
                {"$set": {"status": "resolved", "resolved_at": datetime.now()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking duplicate as resolved: {e}")
            return False
    
    async def delete_duplicate(self, file_id):
        """Mark a duplicate file as deleted"""
        try:
            # This doesn't actually delete the file from storage,
            # it just marks it as a deleted duplicate for record keeping
            await self.duplicates.update_many(
                {"duplicates.file_id": file_id},
                {"$set": {"duplicates.$.deleted": True, "duplicates.$.deleted_at": datetime.now()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting duplicate: {e}")
            return False

# Create global instance
duplicate_detector = DuplicateDetector() 