#!/usr/bin/env python3
"""
Download BraTS 2024 GLI training data from Synapse.

Entity: syn64952546 (BraTS 2024 GLI training folder under BraTS Challenge syn53708249)

Prerequisites:
  1. Register at https://www.synapse.org/ and join BraTS 2024 Challenge
  2. Accept the data use agreement on the Synapse project page
  3. pip install synapseclient
  4. Authenticate (one of):
       synapse login
       synapse login --authToken <PERSONAL_ACCESS_TOKEN>
     Token: Synapse → Settings → Personal Access Tokens

CLI equivalent:
  synapse get -r syn64952546 --downloadLocation data/raw/brats2024_training

Usage:
  python experiments/01_download_brats2024.py --zip-only
  python experiments/01_download_brats2024.py --zip-only --download-list
  python experiments/01_download_brats2024.py --synapse-id syn64952546   # full tree (not recommended)
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


DEFAULT_SYNAPSE_ID = "syn64952546"
DEFAULT_TRAINING_ZIP_ID = "syn60086071"
# BraTS-PTG supplementary demographic information and metadata.xlsx (TCGA linkage hints; small)
DEFAULT_GLI_METADATA_XLSX_ID = "syn64735496"
# BraTS2024-BraTS-GLI-TrainingData.zip v2 (Synapse checksum table)
BRATS_GLI_ZIP_MD5_V2 = "1d910b17d6cd32e38aa6296b8dfb7c77"
BRATS_GLI_ZIP_NAME = "BraTS2024-BraTS-GLI-TrainingData.zip"
DOWNLOAD_LOCK_NAME = ".brats_gli_zip_download.lock"


@contextlib.contextmanager
def _single_download_lock(output: Path):
    """Refuse a second concurrent synapse get on the same training zip (corrupts partial files)."""
    output.mkdir(parents=True, exist_ok=True)
    lock_path = output / DOWNLOAD_LOCK_NAME
    lock_file = open(lock_path, "a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()).encode())
        lock_file.flush()
        yield
    except OSError as exc:
        raise SystemExit(
            f"Another BraTS GLI zip download appears to be running (lock: {lock_path}). "
            "Stop the other process before starting a new download."
        ) from exc
    finally:
        try:
            if sys.platform == "win32":
                import msvcrt

                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()


def _synapse_exe() -> str | None:
    synapse_exe = shutil.which("synapse")
    if synapse_exe is None:
        scripts = Path(sys.executable).parent / "Scripts" / "synapse.exe"
        appdata = Path(os.environ.get("APPDATA", "")) / "Python" / "Python314" / "Scripts" / "synapse.exe"
        for candidate in (scripts, appdata):
            if candidate.exists():
                return str(candidate)
        return None
    return synapse_exe


def download_via_cli(synapse_id: str, output: Path, auth_token: str | None = None) -> bool:
    """Use synapse CLI if on PATH (matches user's synapse get -r workflow)."""
    synapse_exe = _synapse_exe()
    if synapse_exe is None:
        return False

    token = auth_token or os.environ.get("SYNAPSE_AUTH_TOKEN")
    if token:
        subprocess.run(
            [synapse_exe, "login", "-p", token.strip()],
            check=True,
        )

    output.mkdir(parents=True, exist_ok=True)
    cmd = [
        synapse_exe,
        "get",
        "-r",
        synapse_id,
        "--downloadLocation",
        str(output.resolve()),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return True


def _require_disk_space(output: Path, min_free_gb: float = 42.0) -> None:
    """Training zip is ~37.5 GB; refuse early if the volume is too full."""
    output.mkdir(parents=True, exist_ok=True)
    resolved = output.resolve()
    usage = shutil.disk_usage(resolved)
    free_gb = usage.free / (1024**3)
    vol = resolved.drive or resolved.anchor or str(resolved)
    if free_gb < min_free_gb:
        raise SystemExit(
            f"Need at least ~{min_free_gb:.0f} GB free on {vol} "
            f"(got {free_gb:.1f} GB). Free space or set --output / DISSERTATION_BRATS_DIR "
            f"to another drive, then re-run (Synapse resumes if the partial file is still present)."
        )


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        # Prefer .env over stale shell env (common after failed login attempts)
        if key == "SYNAPSE_AUTH_TOKEN" or key not in os.environ:
            os.environ[key] = val


def _login(syn, auth_token: str | None) -> None:
    _load_dotenv()
    token = auth_token or os.environ.get("SYNAPSE_AUTH_TOKEN")
    if token:
        syn.login(authToken=token.strip(), silent=True)
        return
    syn.login(silent=True)


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_zip_if_needed(zip_path: Path, output: Path) -> None:
    if any(output.glob("BraTS-GLI-*")):
        print(f"Extracted cases already present under {output}")
        return
    print(f"Extracting {zip_path.name} -> {output}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(output)


def download_via_download_list(syn, output: Path) -> bool:
    """Download files queued in Synapse web UI cart (user's snippet workflow)."""
    try:
        from synapseclient.operations import download_list_files
    except ImportError:
        return False

    output.mkdir(parents=True, exist_ok=True)
    manifest = download_list_files(synapse_client=syn, download_location=str(output.resolve()))
    print(f"Download list manifest: {manifest}")
    return True


def download_gli_metadata_xlsx(syn, entity_id: str, output: Path) -> Path:
    """Download small GLI metadata spreadsheet (safe while training zip is downloading)."""
    output.mkdir(parents=True, exist_ok=True)
    print(f"Downloading metadata xlsx {entity_id} -> {output}")
    entity = syn.get(entity_id, downloadLocation=str(output.resolve()))
    path = Path(entity.get("path", output / entity.get("name", "metadata.xlsx")))
    print(f"Metadata saved: {path}")
    return path


def download_training_zip_only(
    syn,
    zip_entity_id: str,
    output: Path,
    verify_md5: bool = True,
) -> Path:
    """Download only BraTS2024-BraTS-GLI-TrainingData.zip (recommended; ~48 GB)."""
    output.mkdir(parents=True, exist_ok=True)
    print(f"Downloading training zip {zip_entity_id} -> {output}")
    entity = syn.get(zip_entity_id, downloadLocation=str(output.resolve()))
    zip_name = entity.get("name", BRATS_GLI_ZIP_NAME)
    zip_path = output / zip_name
    if not zip_path.exists():
        matches = list(output.glob(f"*{zip_name}*"))
        zip_path = matches[0] if matches else zip_path
    if zip_path.exists() and verify_md5:
        digest = md5_file(zip_path)
        if digest != BRATS_GLI_ZIP_MD5_V2:
            print(f"WARNING: MD5 mismatch (got {digest}, expected v2 {BRATS_GLI_ZIP_MD5_V2})")
        else:
            print(f"MD5 OK (v2): {digest}")
    if zip_path.exists():
        extract_zip_if_needed(zip_path, output)
    return zip_path


def download_via_python(
    synapse_id: str,
    output: Path,
    auth_token: str | None = None,
    use_download_list: bool = False,
    zip_only: bool = False,
    zip_entity_id: str = DEFAULT_TRAINING_ZIP_ID,
    verify_md5: bool = True,
) -> None:
    import synapseclient

    output.mkdir(parents=True, exist_ok=True)
    syn = synapseclient.Synapse()
    _login(syn, auth_token)
    profile = syn.getUserProfile()
    print(f"Logged in as {profile.get('userName', profile.get('ownerId', 'unknown'))}")

    if zip_only:
        download_training_zip_only(syn, zip_entity_id, output, verify_md5=verify_md5)
        print("Note: BraTS GLI release does not include OS/survival labels in the mapping file.")
        return

    if use_download_list:
        if download_via_download_list(syn, output):
            zip_path = output / BRATS_GLI_ZIP_NAME
            if zip_path.exists() and verify_md5:
                digest = md5_file(zip_path)
                if digest != BRATS_GLI_ZIP_MD5_V2:
                    print(f"WARNING: MD5 mismatch (got {digest}, expected v2 {BRATS_GLI_ZIP_MD5_V2})")
                else:
                    print(f"MD5 OK (v2): {digest}")
            if zip_path.exists():
                extract_zip_if_needed(zip_path, output)
            return

    print(f"Recursive sync {synapse_id} -> {output} (downloads ALL subfolders; prefer --zip-only)")
    import synapseutils

    synapseutils.syncFromSynapse(syn, synapse_id, path=str(output.resolve()))
    print(f"Synced folder {synapse_id}")

    zip_path = output / BRATS_GLI_ZIP_NAME
    if not zip_path.exists():
        matches = list(output.rglob(BRATS_GLI_ZIP_NAME))
        zip_path = matches[0] if matches else None
    if zip_path and zip_path.exists():
        if verify_md5:
            digest = md5_file(zip_path)
            if digest != BRATS_GLI_ZIP_MD5_V2:
                print(f"WARNING: MD5 mismatch (got {digest}, expected v2 {BRATS_GLI_ZIP_MD5_V2})")
            else:
                print(f"MD5 OK (v2): {digest}")
        extract_zip_if_needed(zip_path, output)

    print("Note: BraTS GLI release does not include OS/survival labels in the mapping file.")


def _default_output_dir() -> Path:
    return Path(os.environ.get("DISSERTATION_BRATS_DIR", "data/raw/brats2024_training"))


def main() -> None:
    _load_dotenv()
    parser = argparse.ArgumentParser(description="Download BraTS 2024 GLI from Synapse")
    parser.add_argument("--synapse-id", default=DEFAULT_SYNAPSE_ID)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Download folder (default: DISSERTATION_BRATS_DIR or data/raw/brats2024_training)",
    )
    parser.add_argument("--cli", action="store_true", help="Force synapse CLI instead of Python API")
    parser.add_argument(
        "--auth-token",
        default=None,
        help="Synapse PAT (or set env SYNAPSE_AUTH_TOKEN; never commit tokens)",
    )
    parser.add_argument(
        "--download-list",
        action="store_true",
        help="Use Synapse download cart (add zip in web UI first)",
    )
    parser.add_argument("--no-md5-check", action="store_true")
    parser.add_argument(
        "--full-tree",
        action="store_true",
        help="Sync entire syn64952546 tree (many zips). Default is training zip only.",
    )
    parser.add_argument("--zip-entity-id", default=DEFAULT_TRAINING_ZIP_ID)
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help=f"Download GLI metadata xlsx only ({DEFAULT_GLI_METADATA_XLSX_ID}); does not fetch training zip",
    )
    parser.add_argument("--metadata-entity-id", default=DEFAULT_GLI_METADATA_XLSX_ID)
    args = parser.parse_args()
    if args.output is None:
        args.output = _default_output_dir()
    zip_only = not args.full_tree
    print("Note: run only one BraTS download at a time (avoid parallel synapse get on the same zip).")
    print(f"Output directory: {args.output.resolve()}")

    if args.metadata_only:
        import synapseclient

        syn = synapseclient.Synapse()
        _login(syn, args.auth_token)
        download_gli_metadata_xlsx(syn, args.metadata_entity_id, args.output)
        return

    _require_disk_space(args.output)
    with _single_download_lock(args.output):
        _run_download(args, zip_only)


def _run_download(args: argparse.Namespace, zip_only: bool) -> None:
    try:
        if args.cli:
            if zip_only:
                raise SystemExit("Use Python API for zip download (default). Or: synapse get syn60086071")
            if not download_via_cli(args.synapse_id, args.output, auth_token=args.auth_token):
                raise SystemExit("synapse CLI not found. pip install synapseclient and retry.")
        else:
            try:
                download_via_python(
                    args.synapse_id,
                    args.output,
                    auth_token=args.auth_token,
                    use_download_list=args.download_list,
                    zip_only=zip_only,
                    zip_entity_id=args.zip_entity_id,
                    verify_md5=not args.no_md5_check,
                )
            except Exception as py_err:
                print(f"Python API download failed: {py_err}")
                print("Trying synapse CLI...")
                if not download_via_cli(args.synapse_id, args.output, auth_token=args.auth_token):
                    raise SystemExit(
                        "Synapse login required.\n\n"
                        "Steps:\n"
                        "  1. https://www.synapse.org/ - register\n"
                        "  2. Open https://www.synapse.org/Synapse:syn53708249 - Request Access\n"
                        "  3. pip install synapseclient\n"
                        "  4. synapse login\n"
                        "  5. synapse get -r syn64952546 --downloadLocation data/raw/brats2024_training\n"
                    ) from py_err
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"synapse get failed (exit {exc.returncode}). "
            "Run 'synapse login' first and ensure BraTS 2024 access is approved."
        ) from exc

    zip_path = args.output / BRATS_GLI_ZIP_NAME
    if not zip_path.exists():
        matches = list(args.output.rglob(BRATS_GLI_ZIP_NAME))
        zip_path = matches[0] if matches else None
    if zip_path and zip_path.exists():
        print(f"Zip present: {zip_path} ({zip_path.stat().st_size / 1e9:.2f} GB)")
    elif not any(args.output.rglob("BraTS-GLI-*")):
        print(
            "WARNING: No BraTS-GLI case folders yet. If sync stopped early, re-run this script "
            "(Synapse sync resumes partial downloads)."
        )
    print(f"\nDone. Data in {args.output.resolve()}")


if __name__ == "__main__":
    main()
