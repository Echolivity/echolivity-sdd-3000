"""Render the hardware-replica panel images into dist/ (sdd3k_*.png, 1x and @2x).
Deterministic; needs numpy, scipy and Pillow. Re-run when the panel layout changes,
then run tools/build_amxd.py.   python3 tools/render_panel.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_amxd, hwpanel
print("\n".join(hwpanel.render(build_amxd.panel_spec(), build_amxd.PANEL_DIR)))
