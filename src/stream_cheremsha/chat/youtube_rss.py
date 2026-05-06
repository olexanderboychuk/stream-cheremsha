from __future__ import annotations

from xml.etree import ElementTree as ET

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def extract_video_ids_from_rss_xml(xml: str) -> list[str]:
    root = ET.fromstring(xml)
    out: list[str] = []
    for entry in root.findall("atom:entry", _NS):
        vid = (entry.findtext("yt:videoId", default="", namespaces=_NS) or "").strip()
        if vid:
            out.append(vid)
    return out
