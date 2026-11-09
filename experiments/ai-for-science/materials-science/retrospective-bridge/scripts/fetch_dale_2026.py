#!/usr/bin/env python3
"""Fetch exact active-learning histories from the Dale et al. Zenodo release.

The four source archives total roughly 11 GB because they include checkpoints.
The retrospective bridge needs only the small ``history_test.json`` members.
This script reads each remote ZIP central directory with HTTP ranges, downloads
the 167 eligible histories, and verifies every member against its ZIP metadata.
"""

from __future__ import annotations

import argparse
import binascii
import json
import re
import struct
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass
from pathlib import Path

RECORD = "20754201"
ARCHIVES = {
    1: ("paper1_add_data_part1.zip", "f582c8b1d9e05173e599714b9bb0d60a"),
    2: ("paper1_add_data_part2.zip", "13618666de839cc7bb6521ac7dfaa932"),
    3: ("paper1_add_data_part3.zip", "6389a5806d10c1ef43e35041fee6c086"),
    4: ("paper1_add_data_part4.zip", "f1d83e04657fb9dafff15934dc412df1"),
}
TARGET = re.compile(
    r"^MODEL_PATH/paper1_add_data/"
    r"(bandgap|e_form)_(F|Fe)_"
    r"(0pt05|0pt10|0pt20|0pt50|0pt70|1pt00)_"
    r"(ensem_cal|ensem_cf|ensem_og|ll_cal|ll_cf|ll_og|random)/"
    r"history_test\.json$"
)


@dataclass(frozen=True)
class Member:
    name: str
    compression: int
    crc32: int
    compressed_size: int
    uncompressed_size: int
    local_offset: int


def archive_url(name: str) -> str:
    return f"https://zenodo.org/api/records/{RECORD}/files/{name}/content"


def _range(url: str, start: int, end: int, attempts: int = 5) -> tuple[bytes, str]:
    if end < start:
        raise ValueError(f"invalid byte range {start}-{end}")
    request = urllib.request.Request(
        url,
        headers={
            "Range": f"bytes={start}-{end}",
            "User-Agent": "anarres-source-audit/1",
        },
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request) as response:
                content_range = response.headers.get("Content-Range", "")
                if response.status != 206 or not content_range:
                    raise RuntimeError("server did not honor the HTTP range request")
                return response.read(), content_range
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def _archive_size(content_range: str) -> int:
    match = re.fullmatch(r"bytes \d+-\d+/(\d+)", content_range)
    if not match:
        raise ValueError(f"unexpected Content-Range: {content_range}")
    return int(match.group(1))


def central_directory(url: str) -> tuple[int, list[Member]]:
    _, content_range = _range(url, 0, 0)
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
    directory, _ = _range(url, cd_offset, cd_offset + cd_size - 1)

    members: list[Member] = []
    cursor = 0
    for _ in range(total_entries):
        fields = struct.unpack_from("<4s6H3L5H2L", directory, cursor)
        if fields[0] != b"PK\x01\x02":
            raise ValueError(f"invalid central-directory signature at {cursor}")
        compression = fields[4]
        crc32, compressed_size, uncompressed_size = fields[7:10]
        name_len, extra_len, comment_len = fields[10:13]
        local_offset = fields[-1]
        name_start = cursor + 46
        name = directory[name_start : name_start + name_len].decode("utf-8")
        extra_start = name_start + name_len
        extra = directory[extra_start : extra_start + extra_len]
        if 0xFFFFFFFF in (compressed_size, uncompressed_size, local_offset):
            zip64 = None
            extra_cursor = 0
            while extra_cursor < len(extra):
                header_id, payload_size = struct.unpack_from("<HH", extra, extra_cursor)
                payload = extra[extra_cursor + 4 : extra_cursor + 4 + payload_size]
                if header_id == 0x0001:
                    zip64 = payload
                    break
                extra_cursor += 4 + payload_size
            if zip64 is None:
                raise ValueError(f"ZIP64 values missing for {name}")
            zip64_cursor = 0
            if uncompressed_size == 0xFFFFFFFF:
                uncompressed_size = struct.unpack_from("<Q", zip64, zip64_cursor)[0]
                zip64_cursor += 8
            if compressed_size == 0xFFFFFFFF:
                compressed_size = struct.unpack_from("<Q", zip64, zip64_cursor)[0]
                zip64_cursor += 8
            if local_offset == 0xFFFFFFFF:
                local_offset = struct.unpack_from("<Q", zip64, zip64_cursor)[0]
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


def fetch(output: Path) -> dict:
    records = []
    archive_records = []
    seen: set[tuple[str, str, str, str]] = set()
    for part, (name, md5) in ARCHIVES.items():
        url = archive_url(name)
        size, members = central_directory(url)
        archive_records.append({"part": part, "name": name, "bytes": size, "md5_from_zenodo": md5})
        for member in members:
            match = TARGET.fullmatch(member.name)
            if not match:
                continue
            target, omitted_element, budget, method = match.groups()
            key = (target, omitted_element, budget, method)
            if key in seen:
                raise ValueError(f"duplicate eligible history: {key}")
            seen.add(key)
            relative = Path(target) / omitted_element / budget / method / "history_test.json"
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                content = destination.read_bytes()
                if binascii.crc32(content) & 0xFFFFFFFF != member.crc32:
                    raise ValueError(f"existing file fails CRC32: {destination}")
            else:
                content = fetch_member(url, member)
                destination.write_bytes(content)
            records.append(
                {
                    "part": part,
                    "target": target,
                    "omitted_element": omitted_element,
                    "budget": budget,
                    "method": method,
                    "archive_member": member.name,
                    "relative_path": relative.as_posix(),
                    "crc32": f"{member.crc32:08x}",
                    "bytes": len(content),
                }
            )

    if len(records) != 167:
        raise ValueError(f"expected 167 eligible histories, found {len(records)}")
    manifest = {
        "artifact": "dale_2026_selective_fetch_v1",
        "zenodo_record": f"https://doi.org/10.5281/zenodo.{RECORD}",
        "archives": archive_records,
        "selected_member_count": len(records),
        "members": sorted(
            records,
            key=lambda row: (
                row["target"],
                row["omitted_element"],
                row["budget"],
                row["method"],
            ),
        ),
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
    print(json.dumps({"members": manifest["selected_member_count"]}))


if __name__ == "__main__":
    main()
