# tilekit

tilekit is a tiny toolkit used by a (fictional) game-art team to sanity-check
tile sheets. A sheet is described in a plain-text script: its width, height,
channel count, optional tile size and run-length-encoded pixel data. The tool
can crop, extract tiles, scale and concatenate sheets and prints, for each
result, its dimensions and a 32-bit FNV-1a checksum of the pixel bytes, so the
art pipeline can compare outputs without shipping binary files.

Synthetic benchmark code for defensive evaluation. Everything here is invented.

## Build and run

    ./build.sh                  # produces ./tilekit (ASan + UBSan build)
    ./tilekit < script.txt      # script on stdin, results on stdout

## Script format

One command per line. Blank lines are ignored; `#` starts a comment. Names are
1 to 31 characters from `[A-Za-z0-9_]`. At most 8 images are held at a time.
All numbers are plain decimal. Pixels are bytes, row-major, channels interleaved.

    image NAME W H C [tile TW TH]   start an image block
    rle TOKENS...                   pixel data (only inside a block, may repeat)
    end                             finish the block
    crop DST SRC X Y W H            copy a W x H window whose corner is (X,Y)
    tile DST SRC INDEX              extract tile INDEX (row-major tile grid)
    scale DST SRC FX FY             repeat every pixel FX times across, FY times down
    concat DST A B h|v              join A and B side by side (h) or stacked (v)
    info NAME                       print dimensions, size in bytes, tile size, checksum
    drop NAME                       forget an image

`rle` tokens are `V` (one byte with value V) or `N*V` (N bytes with value V),
V in 0..255, N at least 1. After `end` the data must fill exactly W*H*C bytes.
A DST that names an existing image replaces it (DST may equal a source).

`concat` needs equal channel counts. If the two heights (for `h`) or widths
(for `v`) differ, the shorter or narrower image is padded with zero bytes.
The result of `h` is (Wa+Wb) x max(Ha,Hb); the result of `v` is max(Wa,Wb) x (Ha+Hb).

Every successful command prints one line:

    loaded NAME WxHxC fnv=XXXXXXXX      (after `end`)
    crop|tile|scale|concat DST WxHxC fnv=XXXXXXXX
    info NAME WxHxC bytes=N tile=TWxTH|none fnv=XXXXXXXX
    dropped NAME

## Limits and errors

* W and H must be in 1..16777216 and C in 1..4 (`error: bad dimensions`).
* A declared tile size must satisfy 1 <= TW <= W and 1 <= TH <= H (`error: bad tile size`).
* Scale factors must be in 1..65535 (`error: bad factor`).
* **No image may hold more than 1<<24 (16777216) bytes, W*H*C, whether it is
  declared with `image` or produced by `scale` or `concat`.** Exactly 1<<24 is
  allowed. A request beyond it is rejected with `error: image too large`.
  Nothing is allocated or decoded for a rejected request.

Every error prints one line `error: MESSAGE` on stdout and stops the run at
once (commands before it keep their output). The exit status depends on the kind:

| exit | meaning | messages |
|------|---------|----------|
| 0 | success | |
| 1 | script syntax | `syntax`, `unterminated image` |
| 2 | semantic error | `bad dimensions`, `bad tile size`, `bad factor`, `unknown image`, `too many images`, `pixel data overflow`, `pixel data length mismatch`, `crop out of range`, `no tile size`, `sheet not divisible by tile size`, `tile index out of range`, `channel mismatch`, `out of memory` |
| 3 | size limit | `image too large` |

Checks run in this order for each command: syntax of the line, then lookup of
named images (`unknown image`), then parameter ranges (dimensions, tile size,
factors, crop window, channel match), then the size limit. `rle` data that
would exceed the declared size gives `pixel data overflow`.
