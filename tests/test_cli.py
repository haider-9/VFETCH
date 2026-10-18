from pathlib import Path

import pytest
from yt_dlp.utils import DownloadError

from vfetch import cli
from tests.test_formats import INFO


def run_main(monkeypatch, tmp_path, answers, download):
    inputs = iter(answers)
    monkeypatch.setattr(cli, "read_line", lambda prompt: next(inputs))
    monkeypatch.setattr(cli, "extract", lambda url: INFO)
    monkeypatch.setattr(cli, "run_download", download)
    monkeypatch.setattr(cli, "ffmpeg_path", lambda: "/usr/bin/ffmpeg")
    return cli.main(["https://example.com/v", "-d", str(tmp_path), "--no-color", "--ascii"])


def test_happy_path(monkeypatch, tmp_path, capsys):
    out_file = tmp_path / "Demo [x].mkv"
    out_file.write_bytes(b"x" * 2048)
    code = run_main(monkeypatch, tmp_path, ["1", "y", "n"], lambda *a, **k: (out_file, 65.0))
    out = capsys.readouterr().out
    assert code == 0
    assert "SUCCESS" in out and "2.0 KiB" in out and "01:05" in out


def test_failure_sets_exit_code_and_tip(monkeypatch, tmp_path, capsys):
    def boom(*a, **k):
        raise DownloadError("ERROR: Unable to extract nsig function")

    code = run_main(monkeypatch, tmp_path, ["1", "y", "n"], boom)
    out = capsys.readouterr().out
    assert code == 1
    assert "FAILED" in out and "vfetch --update" in out


def test_cancel_at_confirm(monkeypatch, tmp_path, capsys):
    code = run_main(monkeypatch, tmp_path, ["1", "n", "n"], lambda *a, **k: pytest.fail("should not download"))
    assert code == 0 and "CANCELLED" in capsys.readouterr().out


def test_eof_is_clean_exit(monkeypatch, tmp_path, capsys):
    def eof(prompt):
        raise EOFError

    monkeypatch.setattr(cli, "read_line", eof)
    monkeypatch.setattr(cli, "extract", lambda url: INFO)
    code = cli.main(["https://example.com/v", "-d", str(tmp_path), "--no-color", "--ascii"])
    assert code == 130 and "Traceback" not in capsys.readouterr().out