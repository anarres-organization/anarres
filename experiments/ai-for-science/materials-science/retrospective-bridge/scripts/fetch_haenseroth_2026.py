#!/usr/bin/env python3
"""Fetch selected error artifacts from the Hänseroth et al. Zenodo ZIP.

The released archive is several gigabytes, but the matched benchmark requires
only 21 small ``errors.txt`` members. This script reads the remote ZIP central
directory with HTTP ranges, downloads the selected members, and verifies their
stored CRC32 and uncompressed size.
"""

from __future__ import annotations

import argparse
import binascii
import json
import re
import struct
import urllib.request
import zlib
from dataclasses import dataclass
from pathlib import Path


DEFAULT_URL = (
    "https://zenodo.org/records/20792778/files/"
    "dataset_2000__stride_100_finetune.zip?download=1"
)
ARCHIVE_MD5 = "9d3fedb04578eba7c64fed12055021f3"
PREFIX = "dataset_2000__stride_100_finetune/"
TARGET = re.compile(
    rf"^{re.escape(PREFIX)}(grace_oam|mace_omat|pet_oam)/mace/"
    r"(cdp|cpp|koh|lisi|lpyro|mos2|phoh)/err/errors\.txt$"
)


@dataclass(frozen=True)
class Member:
    name: str
    compression: int
    crc32: int
    compressed_size: int
    uncompressed_size: int
    local_offset: int


def _range(url: str, start: int, end: int | None = None) -> tuple[bytes, str]:
    value = f"bytes={start}-" if end is None else f"bytes={start}-{end}"
    request = urllib.request.Request(url, headers={"Range": value, "User-Agent": "anarres-source-audit/1"})
    with urllib.request.urlopen(request) as response:
        data = response.read()
        content_range = response.headers.get("Content-Range", "")
        if response.status != 206 or not content_range:
            raise RuntimeError("server did not honor the HTTP range request")
        return data, content_range


def _archive_size(content_range: str) -> int:
    match = re.fullmatch(r"bytes \d+-\d+/(\d+)", content_range)
    if not match:
        raise ValueError(f"unexpected Content-Range: {content_range}")
    return int(match.group(1))


def central_directory(url: str) -> tuple[int, list[Member]]:
    probe, content_range = _range(url, 0, 0)
    del probe
    size = _archive_size(content_range)
    tail_start = max(0, size - 65_557)
    tail, _ = _range(url, tail_start, size - 1)
    eocd_at = tail.rfind(b"PK\x05\x06")
    if eocd_at < 0:
        raise ValueError("ZIP end-of-central-directory record not found")
    fields = struct.unpack_from("<4s4H2LH", tail, eocd_at)
    _, disk, cd_disk, disk_entries, total_entries, cd_size, cd_offset, _ = fields
    if disk != 0 or cd_disk != 0 or disk_entries != total_entries:
        raise ValueError("multi-disk ZIP archives are not supported")
    if cd_offset == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
        raise ValueError("ZIP64 archive is not supported")
    directory, _ = _range(url, cd_offset, cd_offset + cd_size - 1)

    members: list[Member] = []
    cursor = 0
    for _ in range(total_entries):
        fields = struct.unpack_from("<4s6H3L5H2L", directory, cursor)
        if fields[0] != b"PK\x01\x02":
            raise ValueError(f"invalid central-directory signature at {cursor}")
        (
            _,
            _,
            _,
            _,
            compression,
            _,
            _,
            crc32,
            compressed_size,
            uncompressed_size,
            name_len,
            extra_len,
            comment_len,
            _,
            _,
            _,
            local_offset,
        ) = fields
        name_start = cursor + 46
        name = directory[name_start : name_start + name_len].decode("utf-8")
        members.append(
            Member(name, compression, crc32, compressed_size, uncompressed_size, local_offset)
        )
        cursor = name_start + name_len + extra_len + comment_len
    if cursor != len(directory):
        raise ValueError("central-directory length mismatch")
    return size, members


def fetch_member(url: str, member: Member) -> bytes:
    local, _ = _range(url, member.local_offset, member.local_offset + 29)
    fields = struct.unpack("<4s5H3L2H", local)
    if fields[0] != b"PK\x03\x04":
        raise ValueError(f"invalid local header for {member.name}")
    name_len, extra_len = fields[-2:]
    data_start = member.local_offset + 30 + name_len + extra_len
    compressed, _ = _range(url, data_start, data_start + member.compressed_size - 1)
    if member.compression == 0:
        content = compressed
    elif member.compression == 8:
        content = zlib.decompress(compressed, -15)
    else:
        raise ValueError(f"unsupported compression method {member.compression}")
    if len(content) != member.uncompressed_size:
        raise ValueError(f"size mismatch for {member.name}")
    if binascii.crc32(content) & 0xFFFFFFFF != member.crc32:
        raise ValueError(f"CRC32 mismatch for {member.name}")
    return content


def fetch(url: str, output: Path) -> dict:
    archive_size, members = central_directory(url)
    targets = [member for member in members if TARGET.fullmatch(member.name)]
    if len(targets) != 21:
        raise ValueError(f"expected 21 matched error files, found {len(targets)}")

    records = []
    for member in sorted(targets, key=lambda item: item.name):
        match = TARGET.fullmatch(member.name)
        assert match is not None
        generator, system = match.groups()
        content = fetch_member(url, member)
        relative = Path(generator) / system / "errors.txt"
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        records.append(
            {
                "generator": generator,
                "system": system,
                "archive_member": member.name,
                "relative_path": relative.as_posix(),
                "crc32": f"{member.crc32:08x}",
                "bytes": len(content),
            }
        )

    manifest = {
        "artifact": "haenseroth_2026_selective_fetch_v1",
        "archive_url": url,
        "archive_md5_from_zenodo": ARCHIVE_MD5,
        "archive_size_bytes": archive_size,
        "selected_member_count": len(records),
        "members": records,
    }
    (output / "FETCH_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = fetch(args.url, args.out)
    print(json.dumps({"members": manifest["selected_member_count"]}))


if __name__ == "__main__":
    main()
