from pathlib import Path

import pytest
import yt_dlp

from vfetch import download
from vfetch.download import QuietLogger, build_options, final_path, run_download


class FakeUI:
    def __init__(self):
        self.updates, self.started, self.finished = [], False, False

    def start(self):
        self.started = True

    def finish(self):
        self.finished = True

    def update(self, **kw):
        self.updates.append(kw)


def make_fake_ydl(tmp_path, captured):
    final = tmp_path / "Video [abc].mkv"
    final.write_bytes(b"x")

    class FakeYDL:
        def __init__(self, options):
            captured.update(options)
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download=True):
            # Intermediate stream files are gone after merging; only the final file exists.
            self.options["progress_hooks"][0](
                {"status": "downloading", "downloaded_bytes": 512, "total_bytes": 1024,
                 "speed": 1834562.7, "eta": 65.4, "info_dict": {"vcodec": "avc1"}}
            )
            self.options["postprocessor_hooks"][0]({"status": "started", "postprocessor": "Merger"})
            return {"requested_downloads": [{"filepath": str(final)}]}

    return FakeYDL, final


def test_run_download_returns_real_path_and_humanized_progress(tmp_path, monkeypatch):
    captured, ui = {}, FakeUI()
    fake, final = make_fake_ydl(tmp_path, captured)
    monkeypatch.setattr(yt_dlp, "YoutubeDL", fake)
    path, elapsed = run_download("https://x.test/v", tmp_path, "1", ui, True)
    assert path == final
    assert elapsed >= 0
    assert ui.started and ui.finished
    first = ui.updates[0]
    assert first["speed"] == "1.7 MiB/s" and first["eta"] == "01:05" and first["pct"] == 50.0
    assert ui.updates[1] == {"label": "MERGING STREAMS"}
    assert isinstance(captured["logger"], QuietLogger)


def test_ui_finish_called_on_error(tmp_path, monkeypatch):
    class Boom:
        def __init__(self, options): pass
        def __enter__(self): return self
        def __exit__(self, *exc): return False
        def extract_info(self, *a, **k): raise yt_dlp.utils.DownloadError("nope")

    monkeypatch.setattr(yt_dlp, "YoutubeDL", Boom)
    ui = FakeUI()
    with pytest.raises(yt_dlp.utils.DownloadError):
        run_download("https://x.test/v", tmp_path, "1", ui, True)
    assert ui.finished


def test_build_options_profiles(tmp_path):
    best = build_options(tmp_path, "1", True)
    assert best["format"] == "bv*+ba/b" and best["merge_output_format"] == "mkv"
    assert {"key": "FFmpegMetadata", "add_metadata": True} in best["postprocessors"]
    assert "embed_metadata" not in best

    mp3 = build_options(tmp_path, "2", True)
    assert mp3["postprocessors"][0]["key"] == "FFmpegExtractAudio"

    no_ff = build_options(tmp_path, "1", False)
    assert no_ff["format"] == "b" and no_ff["postprocessors"] == []

    assert build_options(tmp_path, "137+140", True)["format"] == "137+140"


def test_final_path_ignores_missing_files(tmp_path):
    assert final_path({"requested_downloads": [{"filepath": str(tmp_path / "gone.mp4")}]}) is None
    real = tmp_path / "a.mkv"
    real.write_bytes(b"x")
    assert final_path({"entries": [{"requested_downloads": [{"filepath": str(real)}]}]}) == Path(real)


def test_extract_uses_first_playlist_entry(monkeypatch):
    class FakeYDL:
        def __init__(self, options): pass
        def __enter__(self): return self
        def __exit__(self, *exc): return False
        def extract_info(self, url, download=False):
            return {"entries": [None, {"title": "first", "formats": [1]}]}

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL)
    assert download.extract("https://x.test")["title"] == "first"