#!/bin/bash
# SQLite to PostgreSQL Migration Setup Script

set -e

echo "🚀 SQLite to PostgreSQL Migration Setup"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install migration requirements
echo "📥 Installing migration requirements..."
pip install -r migration_requirements.txt

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  WARNING: DATABASE_URL environment variable is not set"
    echo "   Please set it to your PostgreSQL connection string:"
    echo "   export DATABASE_URL='postgresql://username:password@localhost:5432/database_name'"
    echo ""
    echo "   Or create a .env file with the DATABASE_URL variable"
    echo ""
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Migration cancelled"
        exit 1
    fi
fi

# Check if SQLite database exists
if [ ! -f "smart_lead_router.db" ]; then
    echo "❌ SQLite database 'smart_lead_router.db' not found!"
    echo "   Make sure you're running this from the project root directory"
    exit 1
fi

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "   1. Make sure your PostgreSQL database is running"
echo "   2. Set the DATABASE_URL environment variable"
echo "   3. Run a dry-run test: python migrate_sqlite_to_postgres.py --dry-run"
echo "   4. If dry-run looks good, run the actual migration: python migrate_sqlite_to_postgres.py"
echo ""
echo "📋 Migration will be logged to 'migration.log'"
