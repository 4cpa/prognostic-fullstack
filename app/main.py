from fastapi import FastAPI
from app.api.routes_questions import router as questions_router
from app.api.routes_forecasts import router as forecasts_router

import os
from pathlib import Path


app = FastAPI(title="4CPA Prognostic API", version="0.1.0")

app.include_router(questions_router)
app.include_router(forecasts_router)


@app.get("/health")
def health():
    return {"status": "ok"}


def _read_git_sha(repo_dir: Path) -> str | None:
    """
    Read current git commit SHA without requiring `git` binary.
    Works if `.git` is present in the container (build-based deploy).
    """
    git_dir = repo_dir / ".git"
    head_file = git_dir / "HEAD"

    if not head_file.exists():
        return None

    head = head_file.read_text().strip()

    # HEAD can be:
    # - "ref: refs/heads/main"
    # - or a detached commit SHA
    if head.startswith("ref:"):
        ref_path = head.split(" ", 1)[1].strip()
        ref_file = git_dir / ref_path

        if ref_file.exists():
            return ref_file.read_text().strip()

        # packed-refs fallback
        packed = git_dir / "packed-refs"
        if packed.exists():
            for line in packed.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("^"):
                    continue
                sha, ref = line.split(" ", 1)
                if ref == ref_path:
                    return sha

        return None

    # Detached HEAD
    return head


@app.get("/version")
def version():
    """
    Public via nginx: /api/version
    """
    # Prefer explicit env var if ever provided
    sha = os.environ.get("GIT_SHA")

    # Fallback: read from .git (works in build-based deploy)
    if not sha:
        repo_root = Path(__file__).resolve().parents[1]
        sha = _read_git_sha(repo_root)

    sha = sha or "unknown"

    return {
        "git_sha": sha[:12],
        "service": "prognostic-backend",
        "api_version": app.version,
    }
