# ──────────────────────────────────────────────────────────────
# M-Lab IQB FastAPI — Dockerfile
#
# MUST be built from the REPOSITORY ROOT, not from mlabapi/:
#
#   docker build -f mlabapi/Dockerfile -t mlabapi .
#   docker run --rm -p 8000:8000 mlabapi
#
# The build context must include library/ (local mlab-iqb source)
# because the package is not published to PyPI.
# ──────────────────────────────────────────────────────────────

FROM python:3.13-slim

# Install uv for fast, reproducible dependency management
# (same approach as the prototype Dockerfile in this repo)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# ── 1. Workspace metadata ──────────────────────────────────────
# Copy root pyproject.toml + lockfile first so uv understands
# the workspace layout and can install from the frozen lockfile.
COPY pyproject.toml uv.lock ./

# ── 2. Local dependency (mlab-iqb) ────────────────────────────
# mlab-iqb is NOT on PyPI — it lives in library/.
# Must be present before `uv sync` runs.
COPY library/ ./library/

# ── 3. Application source ─────────────────────────────────────
COPY mlabapi/ ./mlabapi/

# ── 4. Install dependencies ───────────────────────────────────
# --frozen      → use exact versions from uv.lock (no re-resolution)
# --package     → only install deps for the mlabapi workspace member
# --no-dev      → skip dev/test dependencies in production
RUN uv sync --frozen --package mlabapi --no-dev

# ── 5. Runtime config ─────────────────────────────────────────
# PORT can be overridden at runtime (e.g. Cloud Run sets it automatically)
ENV PORT=8000
EXPOSE ${PORT}

WORKDIR /app/mlabapi

# Use shell form so ${PORT} is expanded at runtime
CMD ["sh", "-c", "uv run uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
