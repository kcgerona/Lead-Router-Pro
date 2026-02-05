#!/usr/bin/env python3
"""
Pre-Migration Database Analysis Script

This script analyzes the existing SQLite database to help with migration planning.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

def analyze_sqlite_database():
    """Analyze the SQLite database structure and content"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), "smart_lead_router.db")
    
    if not os.path.exists(db_path):
        print(f"❌ SQLite database not found: {db_path}")
        return
    
    print("🔍 Analyzing SQLite Database Structure")
    print("=" * 50)
    print(f"Database: {db_path}")
    print(f"Size: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
    print()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"📋 Found {len(tables)} tables:")
    for table in sorted(tables):
        print(f"   - {table}")
    print()
    
    # Analyze each table
    analysis = {}
    total_rows = 0
    
    for table_name in tables:
        if table_name == 'sqlite_sequence':
            continue
            
        print(f"📊 Table: {table_name}")
        print("-" * 30)
        
        # Get schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"Columns ({len(columns)}):")
        for col in columns:
            # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
            col_id, col_name, col_type, not_null, default_val, pk = col
            print(f"   - {col_name}: {col_type} {'(PK)' if pk else ''} {'(NOT NULL)' if not_null else ''}")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        total_rows += row_count
        
        print(f"Rows: {row_count:,}")
        
        # Get sample data (first 3 rows)
        if row_count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_rows = cursor.fetchall()
            
            print("Sample data:")
            for i, row in enumerate(sample_rows):
                print(f"   Row {i+1}: {dict(zip([col[1] for col in columns], row))}")
        
        # Store analysis
        analysis[table_name] = {
            "columns": [{"name": col[1], "type": col[2], "primary_key": bool(col[5]), "not_null": bool(col[3])} for col in columns],
            "row_count": row_count
        }
        
        print()
    
    # Summary
    print("📈 Summary")
    print("=" * 50)
    print(f"Total tables: {len(tables)}")
    print(f"Total rows: {total_rows:,}")
    
    # Check for potential issues
    print("\n⚠️  Migration Considerations:")
    
    # Check for JSON columns
    json_tables = []
    for table_name, table_data in analysis.items():
        for col in table_data["columns"]:
            if col["type"].upper() in ["TEXT", "JSON"] and any(keyword in col["name"].lower() for keyword in ["json", "data", "settings", "details"]):
                json_tables.append(f"{table_name}.{col['name']}")
    
    if json_tables:
        print(f"   - Potential JSON columns found: {', '.join(json_tables)}")
    
    # Check for large tables
    large_tables = [(name, data["row_count"]) for name, data in analysis.items() if data["row_count"] > 10000]
    if large_tables:
        print(f"   - Large tables (>10K rows): {', '.join([f'{name} ({count:,})' for name, count in large_tables])}")
    
    # Save analysis to file
    analysis_file = f"sqlite_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(analysis_file, 'w') as f:
        json.dump({
            "database_path": db_path,
            "database_size_mb": os.path.getsize(db_path) / 1024 / 1024,
            "total_tables": len(tables),
            "total_rows": total_rows,
            "tables": analysis
        }, f, indent=2)
    
    print(f"\n💾 Analysis saved to: {analysis_file}")
    
    conn.close()

if __name__ == "__main__":
    analyze_sqlite_database()
