import json
from datetime import datetime
from typing import List

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.database import Base


# デフォルトカテゴリ（全選択）
DEFAULT_CATEGORIES = ["llm", "image", "robotics", "infrastructure"]

# カテゴリの表示名
CATEGORY_LABELS = {
    "llm": "LLM/チャットボット",
    "image": "画像/動画生成",
    "robotics": "ロボティクス/自動運転",
    "infrastructure": "AIインフラ/チップ",
}

# 言語設定の表示名
LANGUAGE_LABELS = {
    "ja": "日本語のみ",
    "en": "英語のみ",
    "both": "両方",
}


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # 配信時間 (0-23)
    delivery_hour = Column(Integer, default=8)

    # カテゴリ (JSON配列: ["llm", "image", "robotics", "infrastructure"])
    categories = Column(Text, default=json.dumps(DEFAULT_CATEGORIES))

    # 言語設定 ("ja", "en", "both")
    language = Column(String(10), default="both")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, hour={self.delivery_hour})>"

    def get_categories(self) -> List[str]:
        """カテゴリリストを取得"""
        try:
            return json.loads(self.categories) if self.categories else DEFAULT_CATEGORIES
        except json.JSONDecodeError:
            return DEFAULT_CATEGORIES

    def set_categories(self, categories: List[str]) -> None:
        """カテゴリリストを設定"""
        self.categories = json.dumps(categories)

    def toggle_category(self, category: str) -> bool:
        """カテゴリのON/OFFを切り替え。戻り値は切り替え後の状態"""
        current = self.get_categories()
        if category in current:
            current.remove(category)
            result = False
        else:
            current.append(category)
            result = True
        self.set_categories(current)
        return result

    def get_language_label(self) -> str:
        """言語設定の表示名を取得"""
        return LANGUAGE_LABELS.get(self.language, "両方")

    def get_categories_label(self) -> str:
        """選択中カテゴリの表示名を取得"""
        categories = self.get_categories()
        if len(categories) == len(DEFAULT_CATEGORIES):
            return "全て"
        elif len(categories) == 0:
            return "なし"
        else:
            return f"{len(categories)}件選択中"
