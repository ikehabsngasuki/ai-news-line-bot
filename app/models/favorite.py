from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    article_id = Column(String(64), ForeignKey("articles.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    article = relationship("Article", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_article"),
    )

    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, article_id={self.article_id})>"
