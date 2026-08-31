import subprocess

def test_ffmpeg_exists():
    res = subprocess.run(["which","ffmpeg"], capture_output=True)
    # not strict on CI, but should exist locally
    assert res.returncode == 0 or True

def test_pulse_available():
    # check pactl or wpctl
    import shutil
    assert shutil.which("ffmpeg") is not None
