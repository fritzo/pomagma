import os
import subprocess


def test_bohm_debug():
    dirname = os.path.dirname(os.path.abspath(__file__))
    subprocess.check_call([os.path.join(dirname, "bohm_debug.py")])
