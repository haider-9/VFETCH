import time

from vfetch.ui import UI


def make_ui(tty=True):
    ui = UI(no_color=True, ascii_mode=True)
    ui.tty = tty
    return ui


def test_second_download_animates_again(capsys):
    ui = make_ui()
    for _ in range(2):  # "Download another?" path
        ui.start()
        ui.update(label="VIDEO", pct=40.0, speed="1.0 MiB/s", eta="00:10", done="4 MiB", total="10 MiB")
        time.sleep(0.35)
        assert ui.frame > 0
        ui.finish()
    out = capsys.readouterr().out
    assert "40.0%" in out


def test_state_resets_between_downloads():
    ui = make_ui()
    ui.start()
    ui.update(label="VIDEO", pct=99.0)
    ui.finish()
    ui.start()
    assert ui.state["pct"] is None and ui.state["label"] == "CONNECTING"
    ui.finish()


def test_postprocess_shows_almost_done(capsys):
    ui = make_ui()
    ui.start()
    ui.update(label="VIDEO", pct=100.0, speed="1 MiB/s", eta="00:00", done="1 MiB", total="1 MiB")
    ui.update(label="MERGING STREAMS")
    time.sleep(0.25)
    ui.finish()
    assert "almost done" in capsys.readouterr().out


def test_piped_output_announces_stages_once(capsys):
    ui = make_ui(tty=False)
    ui.start()
    for _ in range(3):
        ui.update(label="VIDEO", pct=10.0)
    ui.update(label="MERGING STREAMS")
    ui.finish()
    out = capsys.readouterr().out
    assert out.count("[VIDEO]") == 1 and "[MERGING STREAMS]" in out
    assert "\033" not in out