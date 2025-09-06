#!/bin/bash

# Discord Bot Start Script
echo "🚀 Starting Discord Bot..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please run setup.sh first or create .env file manually."
    exit 1
fi

# Start services
echo "📦 Starting Docker containers..."
docker-compose up -d

# Wait a moment for containers to start
sleep 5

# Show status
echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "📝 Bot Logs (last 20 lines):"
docker-compose logs --tail=20 discord-bot

echo ""
echo "✅ Bot started successfully!"
echo ""
echo "Useful commands:"
echo "  View logs: docker-compose logs -f discord-bot"
echo "  Stop bot: docker-compose down"
echo "  Restart: docker-compose restart discord-bot"
echo "  Database UI: http://localhost:8081 (if started with --profile tools)"
