from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Feature, Note, NoteFeature

router = APIRouter(prefix="/features", tags=["features"])


@router.get("")
def list_features(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    product_area: Optional[str] = None,
    owner_id: Optional[int] = None,
    committed: Optional[bool] = None,
    sort: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db),
):
    """List features with filtering and pagination."""
    query = db.query(Feature)

    if product_area:
        query = query.filter(Feature.product_area == product_area)
    if owner_id:
        query = query.filter(Feature.owner_id == owner_id)
    if committed is not None:
        query = query.filter(Feature.committed == committed)

    # Sorting
    sort_col = getattr(Feature, sort, Feature.created_at)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    features = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "data": [_feature_to_dict(f, db) for f in features],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.get("/stats")
def get_features_stats(db: Session = Depends(get_db)):
    """Get aggregate feature statistics."""
    total = db.query(Feature).count()

    # By product area
    by_product_area = (
        db.query(Feature.product_area, func.count(Feature.id))
        .group_by(Feature.product_area)
        .all()
    )

    # By committed status
    committed = db.query(Feature).filter(Feature.committed == True).count()
    uncommitted = db.query(Feature).filter(Feature.committed == False).count()

    # By risk
    by_risk = (
        db.query(Feature.risk, func.count(Feature.id))
        .group_by(Feature.risk)
        .all()
    )

    return {
        "total": total,
        "committed": committed,
        "uncommitted": uncommitted,
        "by_product_area": {pa: c for pa, c in by_product_area if pa},
        "by_risk": {r: c for r, c in by_risk if r},
    }


@router.get("/{feature_id}")
def get_feature(feature_id: int, db: Session = Depends(get_db)):
    """Get a single feature with linked notes."""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        return {"error": "Feature not found"}, 404

    # Get linked notes
    note_links = (
        db.query(Note)
        .join(NoteFeature)
        .filter(NoteFeature.feature_id == feature_id)
        .all()
    )

    result = _feature_to_dict(feature, db)
    result["notes"] = [
        {
            "id": n.id,
            "title": n.title,
            "state": n.state,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in note_links
    ]
    result["note_count"] = len(note_links)

    return result


def _feature_to_dict(feature: Feature, db: Session) -> dict:
    """Convert Feature model to dict."""
    # Count linked notes
    note_count = (
        db.query(NoteFeature)
        .filter(NoteFeature.feature_id == feature.id)
        .count()
    )

    return {
        "id": feature.id,
        "pb_id": feature.pb_id,
        "name": feature.name,
        "description": feature.description,
        "type": feature.type,
        "status": feature.status,
        "product_area": feature.product_area,
        "product_area_stack_rank": feature.product_area_stack_rank,
        "committed": feature.committed,
        "risk": feature.risk,
        "owner_id": feature.owner_id,
        "created_at": feature.created_at.isoformat() if feature.created_at else None,
        "note_count": note_count,
    }
