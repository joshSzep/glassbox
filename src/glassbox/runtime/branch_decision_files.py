"""Changed-file posture for branch-search decision support."""


def changed_files_summary(changed_files: list[str]) -> str:
    if changed_files:
        return ", ".join(changed_files)
    return (
        "Changed-file evidence is not captured in current branch-search "
        "projections; inspect the candidate session before merging work."
    )


__all__ = ["changed_files_summary"]
