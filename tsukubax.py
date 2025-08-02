import os
import subprocess

base_dir = os.path.dirname(__file__)
main_py_path = os.path.join(base_dir, "main.py")

subprocess.run(["python", "-m", "streamlit", "run", main_py_path])

