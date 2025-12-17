from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.orm import relationship

from app.models.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(String(64), primary_key=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(128), nullable=True)
    thumbnail_url = Column(String(2048), nullable=True)

    # スコアリング
    popularity_score = Column(Integer, default=0, index=True)
    hatena_count = Column(Integer, default=0)
    hackernews_score = Column(Integer, default=0)
    reddit_score = Column(Integer, default=0)
    source_count = Column(Integer, default=1)

    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    favorites = relationship("Favorite", back_populates="article", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:30]}...)>"
