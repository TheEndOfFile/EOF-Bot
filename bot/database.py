import os
from pymongo import MongoClient
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            self.client = MongoClient(mongo_uri)
            self.db = self.client['discord_bot']
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def get_collection(self, collection_name):
        """Get a collection from the database"""
        return self.db[collection_name]
    
    # Role Management
    def store_role_request(self, user_id, username, role_name, guild_id, status='pending'):
        """Store a role request in the database"""
        collection = self.get_collection('role_requests')
        request = {
            'user_id': user_id,
            'username': username,
            'role_name': role_name,
            'guild_id': guild_id,
            'status': status,
            'timestamp': datetime.utcnow()
        }
        return collection.insert_one(request)
    
    def update_role_request_status(self, user_id, role_name, status):
        """Update the status of a role request"""
        collection = self.get_collection('role_requests')
        return collection.update_one(
            {'user_id': user_id, 'role_name': role_name},
            {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
        )
    
    def get_user_roles(self, user_id):
        """Get all roles assigned to a user"""
        collection = self.get_collection('role_requests')
        return list(collection.find({'user_id': user_id, 'status': 'approved'}))
    
    # Admin Logging
    def log_admin_action(self, admin_id, admin_username, action, target_id=None, target_username=None, reason=None, guild_id=None):
        """Log admin actions"""
        collection = self.get_collection('admin_logs')
        log_entry = {
            'admin_id': admin_id,
            'admin_username': admin_username,
            'action': action,
            'target_id': target_id,
            'target_username': target_username,
            'reason': reason,
            'guild_id': guild_id,
            'timestamp': datetime.utcnow()
        }
        return collection.insert_one(log_entry)
    
    # User Management
    def store_user_join(self, user_id, username, guild_id, join_date=None):
        """Store user join information"""
        collection = self.get_collection('users')
        if join_date is None:
            join_date = datetime.utcnow()
        
        user_data = {
            'user_id': user_id,
            'username': username,
            'guild_id': guild_id,
            'join_date': join_date,
            'roles': [],
            'last_activity': datetime.utcnow()
        }
        
        # Use upsert to avoid duplicates
        return collection.update_one(
            {'user_id': user_id, 'guild_id': guild_id},
            {'$set': user_data},
            upsert=True
        )
    
    def update_user_activity(self, user_id, guild_id):
        """Update user's last activity"""
        collection = self.get_collection('users')
        return collection.update_one(
            {'user_id': user_id, 'guild_id': guild_id},
            {'$set': {'last_activity': datetime.utcnow()}}
        )
    
    def update_user_roles(self, user_id, guild_id, roles):
        """Update user's roles"""
        collection = self.get_collection('users')
        return collection.update_one(
            {'user_id': user_id, 'guild_id': guild_id},
            {'$set': {'roles': roles}}
        )
    
    # Bug Reports
    def store_bug_report(self, user_id, username, bug_description, guild_id):
        """Store a bug report"""
        collection = self.get_collection('bug_reports')
        bug_report = {
            'user_id': user_id,
            'username': username,
            'description': bug_description,
            'guild_id': guild_id,
            'status': 'open',
            'timestamp': datetime.utcnow()
        }
        return collection.insert_one(bug_report)
    
    def get_bug_reports(self, status='open', limit=10):
        """Get bug reports"""
        collection = self.get_collection('bug_reports')
        return list(collection.find({'status': status}).sort('timestamp', -1).limit(limit))
    
    def update_bug_status(self, bug_id, status):
        """Update bug report status"""
        collection = self.get_collection('bug_reports')
        from bson import ObjectId
        return collection.update_one(
            {'_id': ObjectId(bug_id)},
            {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
        )
    
    # Resources
    def store_resource(self, user_id, username, title, content, url=None, guild_id=None):
        """Store a resource"""
        collection = self.get_collection('resources')
        resource = {
            'user_id': user_id,
            'username': username,
            'title': title,
            'content': content,
            'url': url,
            'guild_id': guild_id,
            'timestamp': datetime.utcnow()
        }
        return collection.insert_one(resource)
    
    def get_resources(self, limit=10):
        """Get recent resources"""
        collection = self.get_collection('resources')
        return list(collection.find().sort('timestamp', -1).limit(limit))
    
    # Leveling System
    def get_user_level_data(self, user_id, guild_id):
        """Get user's level data (XP, level, message count)"""
        collection = self.get_collection('user_levels')
        user_data = collection.find_one({'user_id': user_id, 'guild_id': guild_id})
        if not user_data:
            # Create new user level data
            user_data = {
                'user_id': user_id,
                'guild_id': guild_id,
                'xp': 0,
                'level': 0,
                'message_count': 0,
                'last_xp_gain': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            collection.insert_one(user_data)
        return user_data
    
    def update_user_xp(self, user_id, guild_id, xp_gained, new_level=None):
        """Update user's XP and level"""
        collection = self.get_collection('user_levels')
        update_data = {
            '$inc': {'xp': xp_gained, 'message_count': 1},
            '$set': {'last_xp_gain': datetime.utcnow(), 'updated_at': datetime.utcnow()}
        }
        
        if new_level is not None:
            update_data['$set']['level'] = new_level
        
        return collection.update_one(
            {'user_id': user_id, 'guild_id': guild_id},
            update_data,
            upsert=True
        )
    
    def get_leaderboard(self, guild_id, limit=10, sort_by='xp'):
        """Get server leaderboard"""
        collection = self.get_collection('user_levels')
        return list(collection.find({'guild_id': guild_id}).sort(sort_by, -1).limit(limit))
    
    def get_user_rank(self, user_id, guild_id):
        """Get user's rank in the server"""
        collection = self.get_collection('user_levels')
        user_data = collection.find_one({'user_id': user_id, 'guild_id': guild_id})
        if not user_data:
            return None
        
        # Count users with higher XP
        higher_xp_count = collection.count_documents({
            'guild_id': guild_id,
            'xp': {'$gt': user_data['xp']}
        })
        
        return higher_xp_count + 1  # +1 because rank is 1-indexed
    
    def get_level_stats(self, guild_id):
        """Get server-wide level statistics"""
        collection = self.get_collection('user_levels')
        pipeline = [
            {'$match': {'guild_id': guild_id}},
            {'$group': {
                '_id': None,
                'total_users': {'$sum': 1},
                'total_messages': {'$sum': '$message_count'},
                'total_xp': {'$sum': '$xp'},
                'avg_level': {'$avg': '$level'},
                'max_level': {'$max': '$level'}
            }}
        ]
        result = list(collection.aggregate(pipeline))
        return result[0] if result else None
    
    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")
