def summarize_group_level(metrics: list[dict]) -> dict:
    return {"level": "group", "subject_count": len(metrics), "metrics": metrics}

