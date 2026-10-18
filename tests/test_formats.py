from vfetch.formats import best_pair, group_formats, render_table, size_text

INFO = {
    "title": "Demo",
    "duration": 100,
    "formats": [
        {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a", "height": 360, "width": 640, "tbr": 500, "ext": "mp4"},
        {"format_id": "137", "vcodec": "avc1", "acodec": "none", "height": 1080, "width": 1920, "tbr": 4000, "ext": "mp4", "fps": 30},
        {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "abr": 129.476, "asr": 44100, "ext": "m4a"},
        {"format_id": "sb0", "vcodec": "none", "acodec": "none", "ext": "mhtml"},
    ],
}


def test_group_sort_and_render():
    groups = group_formats(INFO)
    assert groups["VIDEO ONLY"][0]["format_id"] == "137"
    assert "Demo" in render_table(INFO, 70, True)
    assert size_text({"tbr": 800}, 10).startswith("~")


def test_storyboards_skipped():
    assert all(f["format_id"] != "sb0" for g in group_formats(INFO).values() for f in g)


def test_best_pair_requires_video_only_plus_audio():
    assert best_pair(INFO) == "137+140"
    combined_only = {"formats": [INFO["formats"][0], INFO["formats"][2]]}
    assert best_pair(combined_only) == "18"  # never "18+140"


def test_ascii_output_is_ascii_and_fits():
    text = render_table(INFO, 70, True)
    assert text.isascii()
    assert "* best" in text
    assert all(len(line) <= 70 for line in text.splitlines())


def test_no_escape_codes_without_color():
    assert "\033" not in render_table(INFO, 100, False, color=False)
    assert "\033" in render_table(INFO, 100, False, color=True)


def test_bitrate_and_sample_rate_are_readable():
    text = render_table(INFO, 100, True)
    assert "129k" in text and "129.4" not in text
    assert "44.1k" in text and "44100" not in text


def test_best_tag_not_cut_on_narrow_terminal():
    assert "best" in render_table(INFO, 50, True)