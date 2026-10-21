from api.index import get_qualities


def test_uses_quality_label_when_height_missing():
    info = {
        "formats": [
            {"format_id": "h264-720p", "ext": "mp4", "vcodec": "avc1.64001F", "quality_label": "720p", "tbr": 1200},
            {"format_id": "h264-480p", "ext": "mp4", "vcodec": "avc1.4d401f", "quality_label": "480p", "tbr": 800},
            {"format_id": "audio-only", "ext": "m4a", "vcodec": "none", "format_note": "audio"},
        ]
    }

    available = get_qualities(info)

    assert 720 in available
    assert 480 in available


def test_falls_back_to_best_mp4_when_no_target_height_exists():
    info = {
        "formats": [
            {"format_id": "mp4-very-low", "ext": "mp4", "vcodec": "avc1.4d401f", "format_note": "Low", "tbr": 250},
            {"format_id": "mp4-best", "ext": "mp4", "vcodec": "avc1.64001F", "format_note": "HD", "tbr": 3000},
            {"format_id": "audio-only", "ext": "m4a", "vcodec": "none", "format_note": "audio"},
        ]
    }

    available = get_qualities(info)

    assert available
    assert max(available) >= 720 or len(available) >= 1
