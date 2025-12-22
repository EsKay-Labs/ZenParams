import adsk.core
import os
import json

# Global reference for logging
_app = None
_ui = None

def log_diag(msg: str):
    """Writes to the Fusion 360 Text Commands palette."""
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        cmd_palette = ui.palettes.itemById('TextCommands')
        if cmd_palette:
            cmd_palette.writeText(f"[ZenParams] {msg}")
    except:
        pass

class BaseJsonManager:
    """Base class for JSON file management."""
    def __init__(self, root_path: str, filename: str):
        self.file_path = os.path.join(root_path, filename)

    def _read_json(self) -> dict:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log_diag(f"JSON Read Error ({self.file_path}): {e}")
        return {}
        
    def _write_json(self, data: dict):
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            log_diag(f"JSON Write Error ({self.file_path}): {e}")

class PresetManager(BaseJsonManager):
    """Handles loading, saving, and deleting parameter presets."""
    
    def __init__(self, root_path: str):
        super().__init__(root_path, 'user_presets.json')
    
    def get_defaults(self) -> dict:
        """Returns built-in factory presets (3D Printing Optimized)."""
        return {
            "3DP Tolerances (Global)": {
                "Tol_Press": "0.10 mm",
                "Tol_Snug": "0.15 mm",
                "Tol_Slide": "0.25 mm",
                "Tol_Loose": "0.40 mm",
                "Tol_Thread": "0.20 mm", # 3D Printed Threads
                "Tol_Hole": "0.20 mm",   # Vertical Hole Compensation
                "WallThick": "1.2 mm"
            }
        }
    
    def load_all(self) -> dict:
        """Loads both default and user presets."""
        presets = self.get_defaults().copy()
        user_presets = self._read_json()
        presets.update(user_presets)
        return presets
    
    def save_preset(self, name: str, params: dict) -> bool:
        try:
            current = self._read_json()
            current[name] = params
            self._write_json(current)
            return True
        except: return False

    def delete_preset(self, name: str) -> bool:
        try:
            current = self._read_json()
            if name in current:
                del current[name]
                self._write_json(current)
                return True
            return False
        except: return False

class FitManager(BaseJsonManager):
    """Handles Smart Fit default tolerances."""
    
    def __init__(self, root_path: str):
        super().__init__(root_path, 'smart_fits.json')

    def get_defaults(self) -> dict:
        """Hardcoded Factory Defaults."""
        return {
            "bolt": 0.2,
            "magnet": 0.15,
            "bearing": 0.1,
            "insert": -0.1,
            "lid": 0.15,
            "slider": 0.25
        }

    def load_fits(self) -> dict:
        """Merges factory defaults with user overrides."""
        fits = self.get_defaults().copy()
        user_fits = self._read_json()
        fits.update(user_fits)
        return fits

    def save_fits(self, fits_dict: dict) -> bool:
        """Saves user customizations."""
        try:
            self._write_json(fits_dict)
            return True
        except: return False
