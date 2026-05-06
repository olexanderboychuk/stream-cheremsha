from stream_cheremsha.chat.youtube_rss import extract_video_ids_from_rss_xml


def test_extract_video_ids_from_rss_xml_returns_newest_first() -> None:
    xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <feed xmlns=\"http://www.w3.org/2005/Atom\"
          xmlns:yt=\"http://www.youtube.com/xml/schemas/2015\"
          xmlns:media=\"http://search.yahoo.com/mrss/\">
      <entry>
        <yt:videoId>AAAAAAAAAAA</yt:videoId>
      </entry>
      <entry>
        <yt:videoId>BBBBBBBBBBB</yt:videoId>
      </entry>
    </feed>
    """
    assert extract_video_ids_from_rss_xml(xml) == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
