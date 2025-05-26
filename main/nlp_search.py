import logging
from datetime import datetime
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re
import string
from pymongo import MongoClient, TEXT
from pymongo.errors import OperationFailure
from database.db_helpers import get_mongo_client
from info import DATABASE_NAME, OTHER_DB_URI
import motor.motor_asyncio
from database.analytics import analytics_db
from database.tiered_access import tiered_access
import asyncio
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize NLTK components
try:
    import nltk
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
except Exception as e:
    logger.error(f"Error initializing NLTK components: {e}")
    # Fallback to simple tokenization
    stop_words = set(['a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what', 'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than', 'such', 'both', 'through', 'about', 'for', 'is', 'of', 'while', 'during', 'to'])

class NLPSearchEngine:
    def __init__(self):
        """Initialize the NLP search engine with MongoDB connection"""
        self.client = get_mongo_client(OTHER_DB_URI)
        self.db = self.client[DATABASE_NAME]
        self.files = self.db.files
        self.nlp_cache = self.db.nlp_cache
        self.ensure_indexes()
        
    def ensure_indexes(self):
        """Ensure text indexes are created for search performance"""
        try:
            # Create text index on relevant fields
            self.files.create_index([
                ("text", "text"), 
                ("file_name", "text"), 
                ("caption", "text"),
                ("tags", "text")
            ])
            
            # Create index for exact keyword matches
            self.files.create_index("keywords")
            
            # Create index for cache lookup
            self.nlp_cache.create_index("query_hash")
            self.nlp_cache.create_index("timestamp")
            
            logger.info("Search indexes created or already exist")
        except OperationFailure as e:
            logger.error(f"Failed to create index: {e}")

    def preprocess_text(self, text):
        """Preprocess text for better search results"""
        if not text:
            return []
        
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Tokenize
        try:
            tokens = word_tokenize(text)
        except:
            # Fallback if NLTK fails
            tokens = text.split()
        
        # Remove stop words and lemmatize
        try:
            tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words and len(word) > 1]
        except:
            # Fallback if NLTK fails
            tokens = [word for word in tokens if word not in stop_words and len(word) > 1]
            
        return tokens
        
    def extract_keywords(self, query):
        """Extract keywords from a natural language query"""
        tokens = self.preprocess_text(query)
        
        # Extract entities (capitalized words might be titles)
        entities = re.findall(r'\b[A-Z][a-zA-Z0-9]*\b', query)
        
        # Add any numbers (could be years or episode numbers)
        numbers = re.findall(r'\b\d+\b', query)
        
        # Combine all unique tokens
        all_keywords = set(tokens + [e.lower() for e in entities] + numbers)
        
        return list(all_keywords)
    
    def extract_search_context(self, query):
        """Extract contextual information from the query"""
        context = {
            "content_type": None,
            "year": None,
            "quality": None,
            "language": None,
            "season": None,
            "episode": None,
        }
        
        # Check for content type (movie/tv/episode/season)
        if re.search(r'\b(?:tv|television|series)\b', query.lower()):
            context["content_type"] = "tv"
        elif re.search(r'\b(?:movie|film)\b', query.lower()):
            context["content_type"] = "movie"
            
        # Extract year (4 digits)
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        if year_match:
            context["year"] = year_match.group(0)
            
        # Extract quality indicators
        quality_match = re.search(r'\b(?:720p|1080p|2160p|4k|hd|full hd|uhd)\b', query.lower())
        if quality_match:
            context["quality"] = quality_match.group(0)
            
        # Extract season and episode
        season_match = re.search(r'\b(?:s|season)\s*(\d+)\b', query.lower())
        if season_match:
            context["season"] = season_match.group(1)
            
        episode_match = re.search(r'\b(?:e|ep|episode)\s*(\d+)\b', query.lower())
        if episode_match:
            context["episode"] = episode_match.group(1)
            
        return context
    
    def generate_search_query(self, user_query):
        """Generate MongoDB search query from natural language query"""
        keywords = self.extract_keywords(user_query)
        context = self.extract_search_context(user_query)
        
        # Base query with text search
        if keywords:
            query = {
                "$text": {
                    "$search": " ".join(keywords),
                    "$caseSensitive": False,
                    "$diacriticSensitive": False
                }
            }
        else:
            query = {}
        
        # Add context filters if available
        if context["year"]:
            query["year"] = context["year"]
        
        if context["quality"]:
            query["quality"] = {"$regex": context["quality"], "$options": "i"}
            
        if context["season"]:
            query["season"] = context["season"]
            
        if context["episode"]:
            query["episode"] = context["episode"]
            
        if context["content_type"] == "movie":
            query["type"] = {"$in": ["movie", "film"]}
        elif context["content_type"] == "tv":
            query["type"] = {"$in": ["tv", "series", "show"]}
            
        return query
    
    def search(self, query, limit=20):
        """Perform a natural language search and return matches"""
        if not query or len(query.strip()) < 3:
            return []
            
        # Generate query hash for caching
        query_hash = hash(query.lower().strip())
        
        # Check cache first
        cache_hit = self.nlp_cache.find_one({"query_hash": query_hash})
        if cache_hit and (datetime.now() - cache_hit["timestamp"]).total_seconds() < 3600:
            # Cache is fresh (less than 1 hour old)
            return cache_hit["results"]
            
        # Generate MongoDB query
        mongo_query = self.generate_search_query(query)
        
        # Add scoring to results based on text match
        results = list(self.files.find(
            mongo_query,
            {
                "score": {"$meta": "textScore"},
                "file_id": 1, 
                "file_name": 1, 
                "size": 1,
                "caption": 1,
                "type": 1
            }
        ).sort([("score", {"$meta": "textScore"})]).limit(limit))
        
        # Cache results
        self.nlp_cache.update_one(
            {"query_hash": query_hash},
            {
                "$set": {
                    "query": query,
                    "results": results,
                    "timestamp": datetime.now()
                }
            },
            upsert=True
        )
        
        return results

class AsyncNLPSearch:
    def __init__(self):
        """Asynchronous wrapper for NLP search engine"""
        self.search_engine = NLPSearchEngine()
        
    async def search(self, user_id, query, limit=20):
        """Perform search and track analytics"""
        # Check if user can use NLP search (premium feature)
        can_use_nlp = await tiered_access.can_use_feature(user_id, "nlp_search")
        
        if not can_use_nlp:
            # User cannot use NLP search, return empty results
            return {"results": [], "error": "NLP search is a premium feature. Please upgrade your plan."}
            
        # Track this search in analytics
        asyncio.create_task(
            analytics_db.track_activity(
                user_id, 
                "search", 
                query=query, 
                extra_data={"search_type": "nlp"}
            )
        )
        
        # Run the search in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None, 
                lambda: self.search_engine.search(query, limit)
            )
            
            return {"results": results, "error": None}
        except Exception as e:
            logger.error(f"Error in NLP search: {e}")
            return {"results": [], "error": str(e)}

# Create a global instance
nlp_search = AsyncNLPSearch() 