"""Bounded bitmap-glyph recognizer used by the isolated deterministic OCR port.

The recognizer is deliberately small and closed: it reads pixels from a
reviewed 5x7 uppercase/digit model.  It never trusts textual PNG metadata and
never claims a match for an unknown glyph.
"""

from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

_ROWS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "11111"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
}
_BY_PATTERN = {"".join(rows): char for char, rows in _ROWS.items()}


class GlyphOcrError(ValueError):
    pass


def recognize_png(blob: bytes) -> str:
    width, height, pixels = _decode_png(blob)
    ink = [[pixels[y][x] < 128 for x in range(width)] for y in range(height)]
    ink_rows = [y for y in range(height) if any(ink[y])]
    ink_columns = [x for x in range(width) if any(ink[y][x] for y in range(height))]
    if not ink_rows or not ink_columns:
        return ""
    top, bottom = min(ink_rows), max(ink_rows)
    observed_height = bottom - top + 1
    scale = max(1, round(observed_height / 7))
    if not 6 * scale <= observed_height <= 8 * scale:
        raise GlyphOcrError("glyph height does not match the pinned model")
    if scale < 1 or scale > 32:
        raise GlyphOcrError("glyph scale is outside the bounded profile")
    groups: list[tuple[int, int]] = []
    start = previous = ink_columns[0]
    for column in ink_columns[1:]:
        if column != previous + 1:
            groups.append((start, previous))
            start = column
        previous = column
    groups.append((start, previous))
    output: list[str] = []
    previous_end: int | None = None
    for left, right in groups:
        if previous_end is not None and left - previous_end - 1 >= 3 * scale:
            output.append(" ")
        if right - left + 1 != 5 * scale:
            raise GlyphOcrError("glyph width does not match the pinned model")
        bits: list[str] = []
        for row in range(7):
            row_start = top + (row * observed_height) // 7
            row_end = top + ((row + 1) * observed_height) // 7
            for column in range(5):
                count = 0
                samples = 0
                for y in range(row_start, row_end):
                    for dx in range(scale):
                        count += int(ink[y][left + column * scale + dx])
                        samples += 1
                bits.append("1" if count * 2 >= samples else "0")
        char = _BY_PATTERN.get("".join(bits))
        if char is None:
            raise GlyphOcrError("glyph is not present in the pinned model")
        output.append(char)
        previous_end = right
    return "".join(output)


def render_fixture_png(text: str, *, scale: int = 3) -> bytes:
    normalized = text.upper()
    if not normalized or any(char != " " and char not in _ROWS for char in normalized):
        raise ValueError("fixture text contains an unsupported glyph")
    if not 1 <= scale <= 16:
        raise ValueError("fixture scale is invalid")
    margin = 2 * scale
    character_width = 5 * scale
    gap = scale
    word_gap = 4 * scale
    width = 2 * margin
    for index, char in enumerate(normalized):
        width += word_gap if char == " " else character_width
        if index + 1 < len(normalized) and char != " " and normalized[index + 1] != " ":
            width += gap
    height = 7 * scale + 2 * margin
    pixels = [[255 for _ in range(width)] for _ in range(height)]
    cursor = margin
    for index, char in enumerate(normalized):
        if char == " ":
            cursor += word_gap
            continue
        for row, pattern in enumerate(_ROWS[char]):
            for column, bit in enumerate(pattern):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            pixels[margin + row * scale + dy][cursor + column * scale + dx] = 0
        cursor += character_width
        if index + 1 < len(normalized) and normalized[index + 1] != " ":
            cursor += gap
    raw = b"".join(b"\x00" + bytes(row) for row in pixels)
    return _png(width, height, zlib.compress(raw))


def render_fixture_pdf(text: str, *, scale: int = 3) -> bytes:
    """Embed the exact pixel fixture as one PDF image page for OCR tests."""

    width, height, pixels = _decode_png(render_fixture_png(text, scale=scale))
    image = zlib.compress(b"".join(bytes(row) for row in pixels))
    content = f"q {width} 0 0 {height} 0 0 cm /Im0 Do Q".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"
        ).encode("ascii"),
        (
            f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
            f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode /Length {len(image)} >>\n"
        ).encode("ascii")
        + b"stream\n"
        + image
        + b"\nendstream",
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for ordinal, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{ordinal} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(output)


def _decode_png(blob: bytes) -> tuple[int, int, list[list[int]]]:
    if not blob.startswith(b"\x89PNG\r\n\x1a\n"):
        raise GlyphOcrError("input is not PNG")
    offset = 8
    width = height = bit_depth = color_type = None
    compressed = bytearray()
    while offset + 12 <= len(blob):
        length = struct.unpack(">I", blob[offset : offset + 4])[0]
        kind = blob[offset + 4 : offset + 8]
        start, end = offset + 8, offset + 8 + length
        if end + 4 > len(blob):
            raise GlyphOcrError("PNG chunk is truncated")
        payload = blob[start:end]
        expected_crc = struct.unpack(">I", blob[end : end + 4])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            raise GlyphOcrError("PNG chunk checksum is invalid")
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if compression or filtering or interlace:
                raise GlyphOcrError("PNG profile is unsupported")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
        offset = end + 4
    if (
        width is None
        or height is None
        or bit_depth != 8
        or color_type not in {0, 2, 4, 6}
        or width < 1
        or height < 1
        or width * height > 16_777_216
    ):
        raise GlyphOcrError("PNG dimensions or color profile are unsupported")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    row_bytes = width * channels
    cap = (row_bytes + 1) * height
    inflater = zlib.decompressobj()
    raw = inflater.decompress(bytes(compressed), cap + 1)
    if len(raw) > cap or inflater.unconsumed_tail or not inflater.eof:
        raise GlyphOcrError("PNG decompressed size is invalid")
    raw += inflater.flush()
    if len(raw) != cap:
        raise GlyphOcrError("PNG decompressed size is invalid")
    rows: list[bytearray] = []
    cursor = 0
    for _ in range(height):
        filter_kind = raw[cursor]
        cursor += 1
        current = bytearray(raw[cursor : cursor + row_bytes])
        cursor += row_bytes
        prior = rows[-1] if rows else bytearray(row_bytes)
        _unfilter(current, prior, channels, filter_kind)
        rows.append(current)
    grayscale: list[list[int]] = []
    for row in rows:
        values: list[int] = []
        for column in range(width):
            index = column * channels
            if color_type in {0, 4}:
                values.append(row[index])
            else:
                values.append((299 * row[index] + 587 * row[index + 1] + 114 * row[index + 2]) // 1000)
        grayscale.append(values)
    return width, height, grayscale


def _unfilter(current: bytearray, prior: bytearray, bpp: int, kind: int) -> None:
    for index in range(len(current)):
        left = current[index - bpp] if index >= bpp else 0
        up = prior[index]
        upper_left = prior[index - bpp] if index >= bpp else 0
        if kind == 0:
            value = current[index]
        elif kind == 1:
            value = current[index] + left
        elif kind == 2:
            value = current[index] + up
        elif kind == 3:
            value = current[index] + ((left + up) // 2)
        elif kind == 4:
            estimate = left + up - upper_left
            distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
            predictor = (left, up, upper_left)[distances.index(min(distances))]
            value = current[index] + predictor
        else:
            raise GlyphOcrError("PNG filter is unsupported")
        current[index] = value & 0xFF


def _png(width: int, height: int, compressed: bytes) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def _pdf_page(blob: bytes, pdftoppm: Path) -> bytes:
    with tempfile.TemporaryDirectory(prefix="mkb-ocr-pdf-") as root_value:
        root = Path(root_value)
        source = root / "input.pdf"
        prefix = root / "page"
        source.write_bytes(blob)
        completed = subprocess.run(
            (
                str(pdftoppm),
                "-f",
                "1",
                "-l",
                "1",
                "-singlefile",
                "-gray",
                "-r",
                "72",
                "-png",
                str(source),
                str(prefix),
            ),
            capture_output=True,
            check=False,
            timeout=8,
        )
        target = prefix.with_suffix(".png")
        if completed.returncode != 0 or not target.is_file():
            raise GlyphOcrError("PDF page rasterization failed")
        rendered = target.read_bytes()
    if not rendered.startswith(b"\x89PNG"):
        raise GlyphOcrError("PDF page rasterization failed")
    return rendered


def _main() -> int:
    if len(sys.argv) != 3:
        return 64
    media_type, pdftoppm_value = sys.argv[1:]
    blob = sys.stdin.buffer.read(32 * 1024 * 1024 + 1)
    if len(blob) > 32 * 1024 * 1024:
        print("input_limit", file=sys.stderr)
        return 5
    try:
        if media_type == "application/pdf":
            blob = _pdf_page(blob, Path(pdftoppm_value))
        elif media_type != "image/png":
            raise GlyphOcrError("media type is unsupported")
        text = recognize_png(blob)
    except (GlyphOcrError, OSError, subprocess.SubprocessError):
        print("invalid", file=sys.stderr)
        return 2
    if not text.strip():
        print("empty", file=sys.stderr)
        return 3
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["GlyphOcrError", "recognize_png", "render_fixture_pdf", "render_fixture_png"]
