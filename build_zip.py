"""
Build a clean distribution ZIP of RAPR AI.
Run from the project root:  python build_zip.py
"""
import zipfile, os, datetime

name = f"RAPR_AI_v1.6_{datetime.date.today():%Y%m%d}.zip"

skip_dirs = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    "logs", "chat_logs", "helmpack_cache", "packages_cache",
    "unpacked_plan", ".claude",
}
skip_files = {
    ".env", "helmhq.db", "helmhq.db-shm", "helmhq.db-wal",
    "raprai.db", "raprai.db-shm", "raprai.db-wal",
    "credentials.json", ".vault_key", "pyarmor.bug.log",
    "build_zip.py",
}
skip_ext = {".pyc", ".pyo", ".pyd", ".egg", ".zip"}

count = 0
with zipfile.ZipFile(name, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if f in skip_files or any(f.endswith(e) for e in skip_ext):
                continue
            path = os.path.join(root, f)
            zf.write(path, "RAPR_AI/" + path[2:])
            count += 1

size_mb = os.path.getsize(name) / (1024 * 1024)
print(f"✅ Created {name}  ({count} files, {size_mb:.1f} MB)")
