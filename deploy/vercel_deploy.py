"""Create (first time) and deploy the Vercel project, without needing Node or the Vercel CLI.

Usage:  .venv/bin/python deploy/vercel_deploy.py [--project postmanager]
Needs VERCEL_TOKEN in .env (create one at https://vercel.com/account/tokens).
"""

import argparse
import fnmatch
import hashlib
import os
import secrets
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.vercel.com"
EXCLUDE = [".git", ".venv", "media", "staticfiles", "db.sqlite3", ".env", "__pycache__", "*.pyc", ".DS_Store",
           "node_modules", ".idea", ".vscode"]
# Copied from .env to the Vercel project the first time (never overwritten afterwards).
SHARED_SETTINGS = [
    "STUDIO_NAME", "STUDIO_VOICE", "TIME_ZONE", "OWNER_EMAILS", "INSTAGRAM_APP_ID", "INSTAGRAM_APP_SECRET",
    "INSTAGRAM_API_VERSION", "ANTHROPIC_API_KEY", "CAPTION_MODEL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "EMAIL_HOST", "EMAIL_PORT", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "EMAIL_USE_TLS", "DEFAULT_FROM_EMAIL",
    "ACCOUNT_EMAIL_VERIFICATION",
]


class VercelAPI:
    def __init__(self, token, team_id=None):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.params = {"teamId": team_id} if team_id else {}

    def call(self, method, path, ok=(200, 201), **kwargs):
        kwargs["params"] = {**self.params, **kwargs.get("params", {})}
        resp = self.session.request(method, API + path, timeout=120, **kwargs)
        if resp.status_code not in ok:
            try:
                detail = resp.json().get("error", {}).get("message", resp.text)
            except ValueError:
                detail = resp.text
            raise SystemExit(f"Vercel API error ({resp.status_code}) on {path}: {detail}")
        return resp.json() if resp.content else {}


def project_files():
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if path.is_dir() or any(fnmatch.fnmatch(part, pat) for part in rel.parts for pat in EXCLUDE):
            continue
        files.append(rel)
    return files


def ensure_project(api, name):
    resp = api.session.get(f"{API}/v9/projects/{name}", params=api.params, timeout=60)
    if resp.status_code == 200:
        print(f"• Using existing project '{name}'")
        return resp.json()
    if resp.status_code != 404:
        raise SystemExit(f"Could not check project: {resp.status_code} {resp.text}")
    print(f"• Creating project '{name}'")
    return api.call("POST", "/v11/projects", json={"name": name, "framework": None})


def ensure_env(api, project, local_env):
    existing = {e["key"] for e in api.call("GET", f"/v9/projects/{project['id']}/env").get("envs", [])}
    wanted = {
        "SECRET_KEY": secrets.token_urlsafe(50),
        "CRON_SECRET": secrets.token_urlsafe(32),
    }
    for key in SHARED_SETTINGS:
        if local_env.get(key):
            wanted[key] = local_env[key]
    new = [
        {"key": k, "value": v, "type": "encrypted", "target": ["production", "preview"]}
        for k, v in wanted.items() if k not in existing
    ]
    if new:
        api.call("POST", f"/v10/projects/{project['id']}/env", json=new)
        print(f"• Added settings: {', '.join(e['key'] for e in new)}")
    has_db = "DATABASE_URL" in existing or "POSTGRES_URL" in existing
    missing = [k for k, ok in (("DATABASE_URL", has_db), ("BLOB_READ_WRITE_TOKEN", "BLOB_READ_WRITE_TOKEN" in existing)) if not ok]
    return missing


def upload_files(api, files):
    manifest = []
    for i, rel in enumerate(files, 1):
        data = (ROOT / rel).read_bytes()
        sha = hashlib.sha1(data).hexdigest()
        api.call("POST", "/v2/files", data=data, headers={
            "Content-Type": "application/octet-stream", "x-vercel-digest": sha, "Content-Length": str(len(data)),
        })
        manifest.append({"file": rel.as_posix(), "sha": sha, "size": len(data)})
        print(f"\r• Uploading files {i}/{len(files)}", end="", flush=True)
    print()
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", default="postmanager")
    parser.add_argument("--team", help="Vercel team id, if the project belongs to a team")
    parser.add_argument("--force", action="store_true", help="Deploy even if storage isn't connected yet")
    args = parser.parse_args()

    local_env = {**dotenv_values(ROOT / ".env"), **os.environ}
    token = local_env.get("VERCEL_TOKEN")
    if not token:
        raise SystemExit("Add VERCEL_TOKEN=... to the .env file (https://vercel.com/account/tokens).")
    api = VercelAPI(token, args.team or local_env.get("VERCEL_TEAM_ID"))

    project = ensure_project(api, args.project)
    missing = ensure_env(api, project, local_env)
    if missing and not args.force:
        print("\nAlmost ready! In the Vercel dashboard open the project → Storage, then:")
        if "DATABASE_URL" in missing:
            print("   1. Create Database → Neon (Postgres, free) → connect it to this project")
        if "BLOB_READ_WRITE_TOKEN" in missing:
            print("   2. Create Database → Blob (free) → connect it to this project")
        print(f"   https://vercel.com/dashboard → {args.project} → Storage")
        print("Then run this script again to deploy.")
        return 0
    manifest = upload_files(api, project_files())

    print("• Starting deployment")
    deployment = api.call("POST", "/v13/deployments", params={"skipAutoDetectionConfirmation": "1"}, json={
        "name": args.project, "project": project["id"], "target": "production", "files": manifest,
        "projectSettings": {"framework": None},
    })
    inspector = deployment.get("inspectorUrl", "")
    while deployment.get("readyState") not in ("READY", "ERROR", "CANCELED"):
        time.sleep(5)
        deployment = api.call("GET", f"/v13/deployments/{deployment['id']}")
        print(f"\r• Building… {deployment.get('readyState', '')}        ", end="", flush=True)
    print()
    if deployment["readyState"] != "READY":
        raise SystemExit(f"Deployment failed. Build log: {inspector}")

    domains = [a for a in deployment.get("alias", []) if a.endswith(".vercel.app")]
    url = f"https://{domains[0] if domains else deployment['url']}"
    print(f"\n✅ Live at {url}\n   Build details: {inspector}")
    print("\nNext: set up the 5-minute scheduler timer (README → Vercel → step 4).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
