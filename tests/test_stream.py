import subprocess, pathlib, os, shlex

ROOT = pathlib.Path(__file__).resolve().parent.parent
PC_SENDER = ROOT / "src" / "stream" / "pc_sender.sh"
RPI_RECEIVER = ROOT / "src" / "stream" / "rpi_receiver.sh"
GUI = ROOT / "src" / "gui" / "modern_app.py"

def test_scripts_exist():
    assert PC_SENDER.exists(), "pc_sender.sh missing"
    assert RPI_RECEIVER.exists(), "rpi_receiver.sh missing"
    assert GUI.exists(), "modern_app.py missing"

def test_scripts_executable():
    assert os.access(PC_SENDER, os.X_OK)
    assert os.access(RPI_RECEIVER, os.X_OK)

def test_pc_sender_help():
    # dry run should not fail on missing monitor, just check syntax via bash -n
    res = subprocess.run(["bash","-n", str(PC_SENDER)], capture_output=True)
    assert res.returncode == 0, res.stderr.decode()

def test_rpi_receiver_help():
    res = subprocess.run(["bash","-n", str(RPI_RECEIVER)], capture_output=True)
    assert res.returncode == 0, res.stderr.decode()

def test_gui_compile():
    res = subprocess.run(["python3","-m","py_compile", str(GUI)], capture_output=True)
    assert res.returncode == 0, res.stderr.decode()

def test_icon_exists():
    assert (ROOT / "assets" / "icon.png").exists()
    assert (ROOT / "assets" / "icon.svg").exists()

def test_roc_fallback():
    # should fallback if roc not installed, not crash
    # we test that script contains roc logic
    txt = PC_SENDER.read_text()
    assert "roc-send" in txt
    assert "fallback" in txt.lower()
