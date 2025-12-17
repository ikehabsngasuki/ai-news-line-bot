from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
@router.head("/health")
async def health_check():
    """ヘルスチェックエンドポイント（Railway/Render監視用）"""
    return {"status": "healthy"}
