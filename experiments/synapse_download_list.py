#!/usr/bin/env python3
"""
Download BraTS zip from Synapse download cart + verify MD5 v2.

Add BraTS2024-BraTS-GLI-TrainingData.zip (v2) to your Synapse download list in the web UI, then:

  set SYNAPSE_AUTH_TOKEN=your_token_here
  python experiments/synapse_download_list.py

Checksum (v2): 1d910b17d6cd32e38aa6296b8dfb7c77
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from importlib import import_module

download = import_module("01_download_brats2024")


def main() -> None:
    token = os.environ.get("SYNAPSE_AUTH_TOKEN")
    if not token:
        raise SystemExit("Set SYNAPSE_AUTH_TOKEN (never commit tokens to git).")

    import synapseclient

    syn = synapseclient.Synapse()
    download._login(syn, token)
    profile = syn.getUserProfile()
    print(f"Logged in as {profile.get('userName', 'unknown')}")

    out = Path("data/raw/brats2024_training")
    download.download_via_download_list(syn, out)

    zip_path = out / download.BRATS_GLI_ZIP_NAME
    if not zip_path.exists():
        matches = list(out.rglob(download.BRATS_GLI_ZIP_NAME))
        zip_path = matches[0] if matches else None
    if zip_path and zip_path.exists():
        digest = download.md5_file(zip_path)
        if digest == download.BRATS_GLI_ZIP_MD5_V2:
            print(f"MD5 OK (v2): {digest}")
        else:
            print(f"WARNING: MD5 {digest} != expected v2 {download.BRATS_GLI_ZIP_MD5_V2}")
        download.extract_zip_if_needed(zip_path, out)
    else:
        print("Zip not found after download list sync. Add the file to your Synapse cart first.")


if __name__ == "__main__":
    main()
