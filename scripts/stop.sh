#!/bin/bash

# Discord Bot Stop Script
echo "🛑 Stopping Discord Bot..."

# Stop all services
docker-compose down

echo "✅ Bot stopped successfully!"
echo ""
echo "Data is preserved in Docker volumes."
echo "To start again: ./scripts/start.sh or docker-compose up -d"
