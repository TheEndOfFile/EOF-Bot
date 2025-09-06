#!/bin/bash

# Discord Bot Setup Script
echo "🤖 Discord Bot Setup Script"
echo "=========================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "📝 Created .env file from template"
        echo "⚠️  Please edit .env file with your Discord bot token and other settings"
        echo "📖 See README.md for setup instructions"
    else
        echo "❌ env.example file not found"
        exit 1
    fi
else
    echo "✅ .env file exists"
fi

# Create logs directory
mkdir -p logs
echo "✅ Created logs directory"

# Pull Docker images
echo "📥 Pulling Docker images..."
docker-compose pull

# Build bot image
echo "🔨 Building bot image..."
docker-compose build

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Discord bot token and server ID"
echo "2. Create required Discord channels and roles (see README.md)"
echo "3. Start the bot: docker-compose up -d"
echo "4. Check logs: docker-compose logs -f discord-bot"
echo ""
echo "For detailed setup instructions, see README.md"
