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

class PresetManager:
    """Handles loading, saving, and deleting parameter presets."""
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.presets_file = os.path.join(root_path, 'user_presets.json')
    
    def get_defaults(self) -> dict:
        """Returns built-in factory presets (3D Printing Optimized)."""
        return {
            "3DP Tolerances (Global)": {
                "Tol_Press": "0.10 mm",   # Permanent Fit (Bearings/Magnets)
                "Tol_Snug": "0.15 mm",   # Friction Fit (Lids/Snaps)
                "Tol_Slide": "0.25 mm",  # Moving Parts (Slides/Hinges)
                "Tol_Loose": "0.40 mm",  # Easy Fit (Drop-in)
                "Tol_Thread": "0.20 mm", # 3D Printed Threads
                "Tol_Hole": "0.20 mm",   # Vertical Hole Compensation
                "WallThick": "1.2 mm"    # Standard Reference (3 Walls)
            }
        }
    
    def load_all(self) -> dict:
        """Loads both default and user presets."""
        presets = self.get_defaults().copy()
        user_presets = self._read_json()
        presets.update(user_presets)
        return presets
    
    def save_preset(self, name: str, params: dict) -> bool:
        """Saves a new user preset."""
        try:
            current = self._read_json()
            current[name] = params
            self._write_json(current)
            return True
        except Exception as e:
            log_diag(f"Save Preset Error: {e}")
            return False

    def delete_preset(self, name: str) -> bool:
        """Deletes a user preset."""
        try:
            current = self._read_json()
            if name in current:
                del current[name]
                self._write_json(current)
                return True
            return False
        except Exception as e:
            log_diag(f"Delete Preset Error: {e}")
            return False
            
    def _read_json(self) -> dict:
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log_diag(f"JSON Read Error: {e}")
        return {}
        
    def _write_json(self, data: dict):
        with open(self.presets_file, 'w') as f:
            json.dump(data, f, indent=4)
