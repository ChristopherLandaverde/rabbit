"""Public deterministic dataset for API onboarding."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Datasets"])


@router.get("/sample-dataset")
async def sample_dataset():
    path = Path(__file__).resolve().parents[2] / "examples" / "sample_campaigns.csv"
    return FileResponse(
        path, media_type="text/csv", headers={"Cache-Control": "public, max-age=86400"}
    )
