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
    
    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")
