from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class BlogPost(Base):
    __tablename__ = "blog_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    summary = Column(Text)
    content = Column(Text, nullable=False)
    author = Column(String(100), default="Dylan Wiwad")
    published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # For your hockey analytics
    category = Column(String(50), default="deep-dive")  # "deep-dive", "dashboard", etc.
    featured_image = Column(String(255))
    
    def __repr__(self):
        return f"<BlogPost(title='{self.title}', slug='{self.slug}')>"

class NHLPlayer(Base):
    """Model for NHL player data - for your analytics"""
    __tablename__ = "nhl_players"
    
    id = Column(Integer, primary_key=True, index=True)
    nhl_id = Column(Integer, unique=True, index=True)  # NHL API ID
    first_name = Column(String(100))
    last_name = Column(String(100))
    position = Column(String(10))  # C, L, R, D, G
    height_cm = Column(Integer)
    weight_lbs = Column(Integer)
    birth_date = Column(DateTime)
    birth_city = Column(String(100))
    birth_country = Column(String(100))
    
    def __repr__(self):
        return f"<NHLPlayer(name='{self.first_name} {self.last_name}', position='{self.position}')>"

class GameData(Base):
    """Model for NHL game data - for live dashboards"""
    __tablename__ = "game_data"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, unique=True, index=True)  # NHL API game ID
    date = Column(DateTime)
    home_team = Column(String(50))
    away_team = Column(String(50))
    home_score = Column(Integer)
    away_score = Column(Integer)
    status = Column(String(20))  # "scheduled", "live", "final"
    
    def __repr__(self):
        return f"<GameData(game_id={self.game_id}, teams='{self.away_team} @ {self.home_team}')>"