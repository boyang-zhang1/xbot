from datetime import UTC, datetime

from xbot.models import MediaType, TweetThread


def test_thread_from_legacy_converts_media_and_children():
    legacy = {
        "ID": "100",
        "Text": "Root tweet",
        "Timestamp": 1_700_000_000,
        "Photos": [{"ID": "p1", "URL": "https://example.com/p1.jpg"}],
        "Videos": [],
        "Thread": [
            {
                "ID": "101",
                "Text": "Child tweet",
                "Timestamp": 1_700_000_100,
                "Photos": [],
                "Videos": [{"ID": "v1", "URL": "https://example.com/v1.mp4"}],
            }
        ],
    }

    thread = TweetThread.from_legacy("sample_handle", legacy)

    assert thread.author_handle == "sample_handle"
    assert thread.root_id == "100"
    assert thread.tweet_ids == ("100", "101")
    assert thread.root.media[0].media_type == MediaType.PHOTO
    assert thread.tweets[1].media[0].media_type == MediaType.VIDEO
    assert thread.root.timestamp == datetime.fromtimestamp(1_700_000_000, tz=UTC)

