#!/usr/bin/env python3
"""Fetch exact error summaries from Hänseroth and Dreßler (2026)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from fetch_haenseroth_2026 import central_directory, fetch_member

BASE_URL = "https://zenodo.org/records/21198813/files"
SYSTEMS = ("cdp", "cpp", "koh", "lisi", "lpyro", "mos2", "phoh")
FRAMEWORKS = {
    "finetune": ("mace", "sevennet", "grace", "mattersim", "orb"),
    "train": ("mace", "sevennet", "grace"),
}
ARCHIVE_MD5 = {
    "dataset_10__stride_100_finetune.zip": "482124037d271505c1891f13e49a8257",
    "dataset_10__stride_100_train.zip": "0ad0386d9c00e1038edef22e057462da",
    "dataset_10__stride_10_finetune.zip": "9e181a0216a7c5f09a96f777e5016428",
    "dataset_10__stride_10_train.zip": "a4ce82c919e6daeb39c99b661687b8a1",
    "dataset_2000__stride_100_finetune.zip": "c2acefab01c0ee5c93d151af6f250d64",
    "dataset_2000__stride_100_train.zip": "58b8fa367da8afc9e94d8e309abed782",
    "dataset_2000__stride_10_finetune.zip": "0b329a5d8c40fd2a5edcf565ceee5a71",
    "dataset_2000__stride_10_train.zip": "89f6f7896ccaa4e23ddcf7a4cc34255d",
    "dataset_200__stride_100_finetune.zip": "d6f948fdeb7c73386449b81977f0dfd0",
    "dataset_200__stride_100_train.zip": "fc0cc6100f56893358997e0d841ed84e",
    "dataset_200__stride_10_finetune.zip": "6be0a18e249767cf8d5c7c3e2720d51a",
    "dataset_200__stride_10_train.zip": "ce2831b9834e82c2ed8fb62d551d7f2f",
}
ARCHIVE = re.compile(
    r"dataset_(?P<count>10|200|2000)__stride_(?P<stride>10|100)_"
    r"(?P<mode>finetune|train)\.zip"
)


def fetch(output: Path) -> dict:
    archives = []
    for archive_name, archive_md5 in ARCHIVE_MD5.items():
        archive_match = ARCHIVE.fullmatch(archive_name)
        assert archive_match is not None
        metadata = archive_match.groupdict()
        url = f"{BASE_URL}/{archive_name}?download=1"
        archive_size, members = central_directory(url)
        prefix = archive_name.removesuffix(".zip")
        target = re.compile(
            rf"^{re.escape(prefix)}/"
            rf"(?P<framework>{'|'.join(FRAMEWORKS[metadata['mode']])})/"
            rf"(?P<system>{'|'.join(SYSTEMS)})/err/err\.yml$"
        )
        selected = [member for member in members if target.fullmatch(member.name)]
        expected = len(FRAMEWORKS[metadata["mode"]]) * len(SYSTEMS)
        if len(selected) != expected:
            raise ValueError(
                f"expected {expected} error files in {archive_name}, found {len(selected)}"
            )

        records = []
        for member in sorted(selected, key=lambda item: item.name):
            match = target.fullmatch(member.name)
            assert match is not None
            framework, system = match.group("framework", "system")
            content = fetch_member(url, member)
            relative = (
                Path(metadata["mode"])
                / f"n{metadata['count']}_stride{metadata['stride']}"
                / framework
                / system
                / "err.yml"
            )
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            records.append(
                {
                    "framework": framework,
                    "system": system,
                    "archive_member": member.name,
                    "relative_path": relative.as_posix(),
                    "crc32": f"{member.crc32:08x}",
                    "bytes": len(content),
                }
            )
        archives.append(
            {
                "archive": archive_name,
                "archive_url": url,
                "archive_md5_from_zenodo": archive_md5,
                "archive_size_bytes": archive_size,
                "training_configuration_count": int(metadata["count"]),
                "trajectory_stride": int(metadata["stride"]),
                "training_mode": metadata["mode"],
                "selected_member_count": len(records),
                "members": records,
            }
        )

    manifest = {
        "artifact": "haenseroth_dressler_2026_selective_fetch_v1",
        "data_doi": "10.5281/zenodo.21198813",
        "archive_count": len(archives),
        "selected_member_count": sum(item["selected_member_count"] for item in archives),
        "archives": archives,
    }
    (output / "FETCH_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = fetch(args.out)
    print(
        json.dumps(
            {
                "archives": manifest["archive_count"],
                "members": manifest["selected_member_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
