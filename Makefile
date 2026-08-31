.PHONY: install test gui lint clean
install:
	sudo dnf install -y ffmpeg roc-toolkit-utils pipewire-pulse
	pip install -r requirements.txt
test:
	pytest tests/ -v
gui:
	python3 src/gui/modern_app.py
lint:
	shellcheck src/stream/*.sh
	python3 -m py_compile src/gui/*.py
