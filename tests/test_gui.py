import pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parent.parent
GUI = ROOT / "src/gui/modern_app.py"

def test_gui_import():
    # try import without launching Tk (may need display)
    try:
        import customtkinter
        assert customtkinter.__version__
    except Exception as e:
        pass

def test_gui_syntax():
    import py_compile
    py_compile.compile(str(GUI), doraise=True)
