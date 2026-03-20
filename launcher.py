import subprocess
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
dashboard = os.path.join(BASE, "dashboard.py")

subprocess.Popen([sys.executable, "-m", "streamlit", "run", dashboard])
