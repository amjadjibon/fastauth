from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPA_INDEX = _REPO_ROOT / "frontend" / "dist" / "index.html"
_TEMPLATES_DIR = _REPO_ROOT / "templates"

_SPA_ROUTES = ["/", "/login", "/register", "/dashboard", "/admin",
               "/forgot-password", "/reset-password", "/verify-email",
               "/register/success", "/login/mfa", "/dashboard/mfa"]


def _spa_or_template(template_name: str):
    """Return the SPA index.html when the React build exists, else render a Jinja2 template."""
    async def handler(request: Request) -> HTMLResponse:
        if _SPA_INDEX.exists():
            return FileResponse(_SPA_INDEX)
        templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
        return templates.TemplateResponse(request, template_name)
    return handler


router = APIRouter(include_in_schema=False)

router.get("/")((_spa_or_template("login.html")))
router.get("/login")(_spa_or_template("login.html"))
router.get("/register")(_spa_or_template("register.html"))
router.get("/dashboard")(_spa_or_template("dashboard.html"))
router.get("/admin")(_spa_or_template("admin/dashboard.html"))

# SPA-only routes (no Jinja2 fallback needed — these didn't exist before)
for _path in ["/forgot-password", "/reset-password", "/verify-email",
              "/register/success", "/login/mfa", "/dashboard/mfa"]:
    router.get(_path)(_spa_or_template("login.html"))
