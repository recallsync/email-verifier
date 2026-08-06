"""Map internal verification status to list row status."""

INTERNAL_TO_ROW = {
    "valid": "verified",
    "invalid": "failed",
    "risky": "risky",
}

ROW_TO_EXPORT = {
    "verified": "Verified",
    "risky": "Risky",
    "failed": "Failed",
    "skipped": "Skipped",
    "pending": "Pending",
    "processing": "Processing",
}


def map_internal_status(internal_status: str) -> str:
    return INTERNAL_TO_ROW.get(internal_status, "risky")
