# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""Line parsing helpers for stockdesk.

Every command is one line: a command word followed by arguments.  Leading
arguments are single whitespace-delimited tokens; the last argument of some
commands (an item name, a search text) is "the rest of the line" and is kept
verbatim apart from trimming of surrounding whitespace.
"""

MAX_DIGITS = 9


def split_command(line):
    """Return (command, rest) for one input line, or (None, "") if the line is
    blank or a comment (first non-blank character is '#')."""
    text = line.strip()
    if not text or text.startswith("#"):
        return None, ""
    parts = text.split(None, 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def split_fields(rest, count):
    """Split `rest` into `count` leading tokens plus the remainder of the line.

    Returns (tokens, remainder).  If the line has fewer than `count` tokens,
    `tokens` is shorter than `count` and `remainder` is "".
    """
    parts = rest.split(None, count)
    if len(parts) <= count:
        return parts, ""
    return parts[:count], parts[count].strip()


def parse_uint(token):
    """Parse a non-negative decimal integer of at most MAX_DIGITS ASCII digits.
    Returns None when the token is not such a number."""
    if not token or len(token) > MAX_DIGITS:
        return None
    if not (token.isascii() and token.isdigit()):
        return None
    return int(token)


def valid_sku(token):
    """SKUs are 1..16 characters from [A-Za-z0-9_-]."""
    if not token or len(token) > 16:
        return False
    return all(ch.isascii() and (ch.isalnum() or ch in "_-") for ch in token)
