import json
import logging
import re
import zipfile
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Auto Procfile generation
# Maps detected stack + entry point -> start command
# Users never need to create a Procfile manually
# ─────────────────────────────────────────────
PROCFILE_TEMPLATES = {
    "python": {
        "app.py":    "web: gunicorn app:app --bind 0.0.0.0:8080 --workers 2",
        "main.py":   "web: gunicorn main:app --bind 0.0.0.0:8080 --workers 2",
        "server.py": "web: gunicorn server:app --bind 0.0.0.0:8080 --workers 2",
        "run.py":    "web: gunicorn run:app --bind 0.0.0.0:8080 --workers 2",
        "wsgi.py":   "web: gunicorn wsgi:app --bind 0.0.0.0:8080 --workers 2",
        "api.py":    "web: uvicorn api:app --host 0.0.0.0 --port 8080",
        "_default":  "web: gunicorn app:app --bind 0.0.0.0:8080 --workers 2",
    },
    "node": {
        "_default": "web: node index.js",
    },
    "go": {
        "_default": "web: ./main",
    },
    "ruby": {
        "_default": "web: bundle exec ruby app.rb -p 8080",
    },
    "php": {
        "_default": "web: php -S 0.0.0.0:8080",
    },
}

# Frameworks that need uvicorn instead of gunicorn
UVICORN_FRAMEWORKS = ["fastapi", "starlette", "litestar"]

# Env var patterns per language
ENV_VAR_PATTERNS = {
    "python": [
        r'os\.environ\.get\(["\']([A-Z_][A-Z0-9_]*)["\']',
        r'os\.environ\[["\']([A-Z_][A-Z0-9_]*)["\']',
        r'os\.getenv\(["\']([A-Z_][A-Z0-9_]*)["\']',
        r'settings\.([A-Z_][A-Z0-9_]*)',
    ],
    "javascript": [
        r'process\.env\.([A-Z_][A-Z0-9_]*)',
        r'process\.env\[["\']([A-Z_][A-Z0-9_]*)["\']',
        r'import\.meta\.env\.([A-Z_][A-Z0-9_]*)',
        r'Deno\.env\.get\(["\']([A-Z_][A-Z0-9_]*)["\']',
    ],
}

# Env vars we set automatically
PLATFORM_MANAGED_VARS = {
    "PORT",
    "DATABASE_URL",
    "DB_PATH",
    "SQLITE_PATH",
    "NODE_ENV",
    "PYTHON_ENV",
    "HOST",
}

# Stack detection signal files
STACK_SIGNALS = {
    "python": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
    "node": ["package.json"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "php": ["composer.json"],
    "ruby": ["Gemfile"],
    "java": ["pom.xml", "build.gradle"],
}


class PreflightResult(NamedTuple):
    stack: str
    required_env_vars: list[str]
    has_sqlite: bool
    entry_point: str
    warnings: list[str]
    errors: list[str]
    procfile_content: str   # Auto-generated Procfile content
    needs_procfile: bool    # Whether we need to inject a Procfile


def scan_zip(zip_path: str) -> PreflightResult:
    """
    Scans a user's uploaded zip file.
    Detects stack, env vars, SQLite usage, entry points.
    Auto-generates a Procfile if one is missing.
    """
    required_vars: set[str] = set()
    warnings: list[str] = []
    errors: list[str] = []
    stack = "unknown"
    has_sqlite = False
    entry_point = ""
    has_procfile = False
    procfile_content = ""
    package_json_content = ""

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            file_list = zf.namelist()
            prefix = _detect_zip_prefix(file_list)
            stack = _detect_stack(file_list, prefix)

            # Check if Procfile already exists
            normalized_files = [f[len(prefix):] for f in file_list]
            has_procfile = "Procfile" in normalized_files

            # Read package.json if Node app
            if stack == "node" and "package.json" in normalized_files:
                for file_path in file_list:
                    if file_path[len(prefix):] == "package.json":
                        try:
                            package_json_content = zf.read(file_path).decode("utf-8", errors="ignore")
                        except Exception:
                            pass
                        break

            # Scan source files
            requirements_content = ""
            for file_path in file_list:
                normalized = file_path[len(prefix):]

                # Read requirements.txt for framework detection
                if normalized == "requirements.txt":
                    try:
                        requirements_content = zf.read(file_path).decode("utf-8", errors="ignore").lower()
                    except Exception:
                        pass

                if not _is_source_file(normalized):
                    continue

                try:
                    content = zf.read(file_path).decode("utf-8", errors="ignore")
                except Exception:
                    continue

                vars_found = _extract_env_vars(content, stack)
                required_vars.update(vars_found)

                if _detect_sqlite(content):
                    has_sqlite = True

            # Detect entry point
            entry_point = _detect_entry_point(file_list, prefix, stack)
            if not entry_point:
                warnings.append(
                    "Could not detect app entry point. "
                    "Nixpacks will attempt auto-detection."
                )

            if stack == "unknown":
                errors.append(
                    "Could not detect app stack. "
                    "Ensure your project has package.json (Node.js) "
                    "or requirements.txt (Python)."
                )

    except zipfile.BadZipFile:
        errors.append("Uploaded file is not a valid zip archive.")
    except Exception as e:
        logger.error(f"Pre-flight scan error: {e}")
        errors.append(f"Failed to scan uploaded file: {str(e)}")

    # Auto-generate Procfile if missing
    needs_procfile = not has_procfile and stack != "unknown"
    if needs_procfile:
        procfile_content = _generate_procfile(
            stack, entry_point, requirements_content, package_json_content
        )
        logger.info(f"Auto-generated Procfile: {procfile_content}")

    user_required_vars = sorted(
        [v for v in required_vars if v not in PLATFORM_MANAGED_VARS]
    )

    return PreflightResult(
        stack=stack,
        required_env_vars=user_required_vars,
        has_sqlite=has_sqlite,
        entry_point=entry_point,
        warnings=warnings,
        errors=errors,
        procfile_content=procfile_content,
        needs_procfile=needs_procfile,
    )


def _generate_procfile(
    stack: str,
    entry_point: str,
    requirements_content: str = "",
    package_json_content: str = "",
) -> str:
    """
    Auto-generate the correct Procfile start command.

    Priority order:
    1. package.json scripts.start (Node apps)
    2. Framework-specific detection (FastAPI vs Flask)
    3. Entry point matching
    4. Stack default fallback
    """

    # ── Node.js: read start script from package.json ──
    if stack == "node" and package_json_content:
        try:
            pkg = json.loads(package_json_content)
            scripts = pkg.get("scripts", {})

            # Prefer "start" script, fall back to "serve" or "dev"
            start_cmd = scripts.get("start") or scripts.get("serve")
            if start_cmd:
                # Replace hardcoded ports with PORT env var
                start_cmd = re.sub(r'port\s+\d+', 'port $PORT', start_cmd, flags=re.IGNORECASE)
                start_cmd = re.sub(r':\d{4,5}', ':$PORT', start_cmd)
                return f"web: {start_cmd}"

            # Check main field
            main = pkg.get("main", "index.js")
            return f"web: node {main}"

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Could not parse package.json: {e}")
            return PROCFILE_TEMPLATES["node"]["_default"]

    # ── Python: detect framework from requirements.txt ──
    if stack == "python":
        templates = PROCFILE_TEMPLATES["python"]

        # Check if it's a FastAPI/uvicorn app
        is_uvicorn = any(fw in requirements_content for fw in UVICORN_FRAMEWORKS)

        if is_uvicorn:
            # Detect the module name from entry point
            module = "main"
            if entry_point:
                module = Path(entry_point).stem
            return f"web: uvicorn {module}:app --host 0.0.0.0 --port 8080"

        # Match entry point to template
        if entry_point and entry_point in templates:
            return templates[entry_point]

        # Use entry point to construct gunicorn command
        if entry_point:
            module = Path(entry_point).stem
            return f"web: gunicorn {module}:app --bind 0.0.0.0:8080 --workers 2"

        return templates["_default"]

    # ── Other stacks: use default ──
    templates = PROCFILE_TEMPLATES.get(stack, {})
    return templates.get("_default", "web: ./start.sh")


def inject_procfile_into_zip(zip_path: str, procfile_content: str, output_path: str) -> str:
    """
    Creates a new zip with the Procfile injected.
    Returns path to the new zip.
    Called by the deployment service before uploading to S3.
    """
    import tempfile
    import shutil

    logger.info(f"Injecting Procfile into zip: {procfile_content}")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    # Copy existing zip and add Procfile
    shutil.copy2(zip_path, tmp_path)

    with zipfile.ZipFile(tmp_path, "a") as zf:
        # Check if there's a prefix (single subdirectory)
        file_list = zf.namelist()
        prefix = _detect_zip_prefix(file_list)

        # Add Procfile at the right level
        procfile_path = f"{prefix}Procfile" if prefix else "Procfile"
        zf.writestr(procfile_path, procfile_content)

    return tmp_path


# ─────────────────────────────────────────────
# Internal helpers (unchanged)
# ─────────────────────────────────────────────

def _detect_zip_prefix(file_list: list[str]) -> str:
    if not file_list:
        return ""
    top_level = set()
    for f in file_list:
        parts = f.split("/")
        if parts[0]:
            top_level.add(parts[0])
    if len(top_level) == 1:
        prefix = list(top_level)[0] + "/"
        all_under_prefix = all(f.startswith(prefix) for f in file_list if f)
        if all_under_prefix:
            return prefix
    return ""


def _detect_stack(file_list: list[str], prefix: str) -> str:
    normalized = [f[len(prefix):] for f in file_list]
    for stack, signals in STACK_SIGNALS.items():
        for signal in signals:
            if signal in normalized:
                return stack
    return "unknown"


def _is_source_file(path: str) -> bool:
    source_extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".mjs", ".cjs", ".go", ".rb", ".php"
    }
    skip_dirs = {
        "node_modules", ".git", "__pycache__",
        ".venv", "venv", "dist", "build", ".next"
    }
    parts = Path(path).parts
    if any(part in skip_dirs for part in parts):
        return False
    return Path(path).suffix in source_extensions


def _extract_env_vars(content: str, stack: str) -> set[str]:
    found = set()
    patterns = []
    if stack == "python":
        patterns = ENV_VAR_PATTERNS["python"]
    elif stack in ("node", "unknown"):
        patterns = ENV_VAR_PATTERNS["javascript"]
    else:
        patterns = ENV_VAR_PATTERNS["python"] + ENV_VAR_PATTERNS["javascript"]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if match.isupper() and 2 <= len(match) <= 50:
                found.add(match)
    return found


def _detect_sqlite(content: str) -> bool:
    sqlite_patterns = [
        r"sqlite",
        r"\.db['\"]",
        r"SQLite",
        r"from sqlalchemy.*sqlite",
        r"sqlite3\.connect",
        r"better-sqlite3",
    ]
    content_lower = content.lower()
    return any(re.search(p, content_lower) for p in sqlite_patterns)


def _detect_entry_point(file_list: list[str], prefix: str, stack: str) -> str:
    normalized = [f[len(prefix):] for f in file_list]
    if stack == "python":
        candidates = ["main.py", "app.py", "server.py", "run.py", "wsgi.py", "api.py"]
        for candidate in candidates:
            if candidate in normalized:
                return candidate
    elif stack == "node":
        if "package.json" in normalized:
            return "package.json"
    return ""