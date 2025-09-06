// MongoDB initialization script
// This script runs when the MongoDB container starts for the first time

db = db.getSiblingDB('discord_bot');

// Create collections with indexes for better performance
db.createCollection('role_requests');
db.role_requests.createIndex({ "user_id": 1, "guild_id": 1 });
db.role_requests.createIndex({ "status": 1 });
db.role_requests.createIndex({ "timestamp": -1 });

db.createCollection('admin_logs');
db.admin_logs.createIndex({ "admin_id": 1 });
db.admin_logs.createIndex({ "guild_id": 1 });
db.admin_logs.createIndex({ "timestamp": -1 });
db.admin_logs.createIndex({ "action": 1 });

db.createCollection('users');
db.users.createIndex({ "user_id": 1, "guild_id": 1 }, { unique: true });
db.users.createIndex({ "join_date": -1 });
db.users.createIndex({ "last_activity": -1 });

db.createCollection('bug_reports');
db.bug_reports.createIndex({ "user_id": 1 });
db.bug_reports.createIndex({ "guild_id": 1 });
db.bug_reports.createIndex({ "status": 1 });
db.bug_reports.createIndex({ "timestamp": -1 });

db.createCollection('resources');
db.resources.createIndex({ "user_id": 1 });
db.resources.createIndex({ "guild_id": 1 });
db.resources.createIndex({ "timestamp": -1 });
db.resources.createIndex({ "title": "text", "content": "text" });

print('Database initialization completed successfully!');
print('Collections created: role_requests, admin_logs, users, bug_reports, resources');
print('Indexes created for optimal performance');
