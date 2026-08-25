"""Rich-text chat lines: stable nickname colors, platform icons, emoji-safe escaping."""

from __future__ import annotations

import base64
import colorsys
import hashlib
import html
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from stream_cheremsha.domain.models import ChatMessage, ChatPlatform

CHAT_ICON_PX = 18
# Whitespace between time / platform icon / nick (Qt often ignores margin on <span>).
CHAT_HEADER_GAP = "\u00a0" * 2
# Default when nothing is in QSettings; must match the chat toolbar initial selection.
CHAT_DEFAULT_FONT_FAMILY = "Segoe WP Black"


def author_color_hex(author: str) -> str:
    """Stable saturated color per author, readable on dark backgrounds."""
    digest = hashlib.sha256(author.casefold().encode("utf-8")).digest()
    hue = ((digest[0] << 8 | digest[1]) % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.72, 0.58)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def chat_font_stack_css(primary_family: str) -> str:
    """CSS font-family stack with emoji-capable fallbacks after the user font."""
    base = (primary_family or "").strip().replace("'", "").replace(
        '"', ""
    ) or CHAT_DEFAULT_FONT_FAMILY
    return (
        f"'{base}','Segoe UI Emoji','Apple Color Emoji','Noto Color Emoji',"
        f"'Noto Sans','DejaVu Sans',sans-serif"
    )


def svg_file_to_png_data_uri(svg_path: Path, out_px: int = CHAT_ICON_PX) -> str | None:
    """Rasterize SVG to a PNG data URI for QTextDocument (reliable vs. inline SVG)."""
    if not svg_path.is_file():
        return None
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        return None
    img = QImage(out_px, out_px, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    if not img.save(buf, "PNG"):
        return None
    b64 = base64.standard_b64encode(ba.data()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def load_platform_icon_data_uris(
    assets_dir: Path,
) -> tuple[str | None, str | None, str | None, str | None]:
    return (
        svg_file_to_png_data_uri(assets_dir / "twitch.svg"),
        svg_file_to_png_data_uri(assets_dir / "youtube.svg"),
        svg_file_to_png_data_uri(assets_dir / "tiktok.svg"),
        svg_file_to_png_data_uri(assets_dir / "kick.svg"),
    )


def format_chat_message_html(
    message: ChatMessage,
    *,
    font_pt: int,
    font_stack_css: str,
    twitch_icon_uri: str | None,
    youtube_icon_uri: str | None,
    tiktok_icon_uri: str | None = None,
    kick_icon_uri: str | None = None,
) -> str:
    if message.platform is ChatPlatform.TWITCH:
        uri = twitch_icon_uri
    elif message.platform is ChatPlatform.YOUTUBE:
        uri = youtube_icon_uri
    elif message.platform is ChatPlatform.TIKTOK:
        uri = tiktok_icon_uri
    elif message.platform is ChatPlatform.KICK:
        uri = kick_icon_uri
    else:
        uri = tiktok_icon_uri
    if uri:
        # Inline next to the nick; a 2-col table in QTextEdit stretched a huge gap.
        icon_html = (
            f'<img src="{uri}" width="{CHAT_ICON_PX}" height="{CHAT_ICON_PX}" '
            'style="display:inline; vertical-align:middle; '
            f'margin:0 3px 0 3px;"/>'  # space around icon vs time & nick
        )
    else:
        icon_html = ""

    ts = html.escape(message.received_at.strftime("%H:%M:%S"), quote=True)
    auth_esc = html.escape(message.author, quote=True)
    text_esc = html.escape(message.text, quote=True)
    nick_color = author_color_hex(message.author)
    block_style = f"line-height:1.35;font-size:{font_pt}pt;font-family:{font_stack_css};"
    # time → icon (optional) → nick → : → body. Fragment only: real line break comes from
    # MainWindow._append_chat (insertBlock), not a second <p> in one QTextBlock.
    return (
        f'<div style="margin:0 0 3px 0;{block_style}">'
        f'<span style="color:#64748b;font-size:0.88em;">{ts}</span>'
        f"{CHAT_HEADER_GAP}{icon_html}{CHAT_HEADER_GAP if icon_html else ''}"
        f'<span style="font-weight:600;color:{nick_color};">{auth_esc}</span>'
        f'<span style="color:#64748b;">:</span> '
        f'<span style="color:#e2e8f0;white-space:pre-wrap;word-wrap:break-word;">{text_esc}</span>'
        f"</div>"
    )
