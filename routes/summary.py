from fastapi import APIRouter, Request, Query
from typing import Optional

router = APIRouter(prefix="/payments/summary", tags=["summary"])


@router.get("/")
async def get_summary(
    request: Request,
    user_id: str = Query(...),
    period: Optional[str] = Query(None, description="Format: YYYY-MM, e.g. 2026-05"),
):
    db = request.app.state.db

    match: dict = {"user_id": user_id}
    if period:
        match["period"] = period

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$status",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }
        },
        {
            "$group": {
                "_id": None,
                "by_status": {
                    "$push": {
                        "status": "$_id",
                        "total": "$total",
                        "count": "$count",
                    }
                },
                "grand_total": {"$sum": "$total"},
                "total_count": {"$sum": "$count"},
            }
        },
        {"$project": {"_id": 0, "by_status": 1, "grand_total": 1, "total_count": 1}},
    ]

    results = await db["payments"].aggregate(pipeline).to_list(length=1)

    if not results:
        return {
            "user_id": user_id,
            "period": period,
            "grand_total": 0,
            "total_count": 0,
            "by_status": [],
        }

    return {"user_id": user_id, "period": period, **results[0]}
