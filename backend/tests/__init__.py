from pathlib import Path

# Portable path to the repository root, two levels above backend/tests/.
REPO_ROOT = Path(__file__).resolve().parents[2]

# Convenience helpers for locating frontend source files.
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"

# All authenticated pages live inside the (workspace) Next.js route group.
# Route groups are URL-transparent: /evidence and /(workspace)/evidence
# resolve to the same public URL but the source file is under (workspace).
WORKSPACE_PAGES = FRONTEND_SRC / "app" / "(workspace)"


def workspace_page(route: str) -> Path:
    """Return the absolute Path for an authenticated workspace page source file.

    Example::

        workspace_page("evidence/page.tsx")
        # → .../frontend/src/app/(workspace)/evidence/page.tsx

    This is the canonical way for backend tests to reference frontend pages
    that were migrated into the (workspace) route group.  Update callers here
    if the layout ever changes again rather than scattering raw path strings
    across test files.
    """
    return WORKSPACE_PAGES / route
