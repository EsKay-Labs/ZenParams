
# 🧘 ZenParams Pro - Entry Point
import adsk.core, traceback
import os, sys

# Ensure local source directory is in path
APP_PATH = os.path.dirname(os.path.abspath(__file__))
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)

# Global Access
_addin = None

def run(context):
    global _addin
    try:
        from src.app import ZenParamsAddin
        _addin = ZenParamsAddin()
        _addin.run()
    except:
        adsk.core.Application.get().userInterface.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    global _addin
    if _addin:
        _addin.stop()
        _addin = None
