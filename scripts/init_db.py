#!/usr/bin/env python3
"""
Database initialization script
Run this to set up your database with sample data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Base, BlogPost
from datetime import datetime

def init_database():
    """Initialize database with sample data"""
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if we already have data
        existing_posts = db.query(BlogPost).count()
        if existing_posts > 0:
            print(f"Database already has {existing_posts} blog posts. Skipping initialization.")
            return
        
        # Add your existing blog posts to database
        sample_posts = [
            BlogPost(
                title="How have player demographics changed over the history of the league?",
                slug="historical-player-demographics-2025",
                summary="A deep exploration of player height, weight, and nationality from 1917-2025.",
                content="<p>Your full blog post content would go here...</p>",
                category="deep-dive",
                published=True,
                created_at=datetime(2025, 7, 20)
            ),
            BlogPost(
                title="How have career tenure and trajectories changed over the history of the league?",
                slug="player-career-tenure-2025", 
                summary="A deep exploration of player career tenure from 1917-2025.",
                content="<p>Your full blog post content would go here...</p>",
                category="deep-dive",
                published=True,
                created_at=datetime(2025, 7, 25)
            )
        ]
        
        # Add to database
        for post in sample_posts:
            db.add(post)
        
        db.commit()
        print(f"Successfully initialized database with {len(sample_posts)} blog posts!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()