from __future__ import annotations

from typing import Optional
import re

import bleach


ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
    'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'img'
]

def _img_attr_filter(tag: str, name: str, value: str):
    # Allow only our served files and safe text attributes
    try:
        if name == 'src':
            v = (value or '').strip()
            return v if v.startswith('/api/v1/files/') else None
        if name in ('alt', 'title'):
            return value
    except Exception:
        return None
    return None

ALLOWED_ATTRS = {
    'a': ['href', 'title'],
    # preserve indentation level for Quill lists via data attribute
    'li': ['data-indent'],
    'img': _img_attr_filter,
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def _preprocess_quill_list_indents(raw_html: str) -> str:
    """Add data-indent attributes for list items that use Quill's ql-indent-N classes.

    We do this BEFORE bleach so that even if class attributes are stripped,
    we can still preserve indentation level via data-indent.
    """
    out = raw_html
    # Double-quoted class
    out = re.sub(
        r"(<li\b[^>]*?)class=\"([^\"]*?ql-indent-(\d+)[^\"]*?)\"([^>]*?)>",
        lambda m: f"{m.group(1)}data-indent=\"{m.group(3)}\"{m.group(4)}>",
        out,
        flags=re.IGNORECASE,
    )
    # Single-quoted class
    out = re.sub(
        r"(<li\b[^>]*?)class='([^']*?ql-indent-(\d+)[^']*?)'([^>]*?)>",
        lambda m: f"{m.group(1)}data-indent=\"{m.group(3)}\"{m.group(4)}>",
        out,
        flags=re.IGNORECASE,
    )
    return out


def sanitize_comment_html(html: Optional[str]) -> str | None:
    if not html:
        return None
    try:
        html = _preprocess_quill_list_indents(html)
    except Exception:
        pass
    # Restrict external images: allow only src that starts with our files prefix
    def _attr_filter(tag, name, value):  # type: ignore[no-redef]
        if tag == 'img' and name == 'src':
            try:
                v = (value or '').strip()
                return v.startswith('/api/v1/files/')
            except Exception:
                return False
        return True

    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned or None


