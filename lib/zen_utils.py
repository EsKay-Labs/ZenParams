import adsk.core
import os
import json

# Global reference for logging
_app = None
_ui = None
APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

def log_file(msg: str):
    """Writes to a log file to avoid Event Loop Freezes."""
    try:
        log_path = os.path.join(APP_PATH, 'zen_debug.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"{time.ctime()}: {msg}\n")
    except: pass

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
    """Handles Smart Fit default tolerances with categorization and customization."""
    
    def __init__(self, root_path: str):
        super().__init__(root_path, 'smart_fits.json')

    def get_defaults(self) -> list:
        """Returns structured default fits."""
        return [
            # 3D Printing Standard
            {"id": "bolt",    "label": "Bolt Clearance",   "group": "3D Printing", "tol": 0.2},
            {"id": "magnet",  "label": "Magnet Press Fit", "group": "3D Printing", "tol": 0.15},
            {"id": "bearing", "label": "Bearing Press Fit","group": "3D Printing", "tol": 0.1},
            {"id": "insert",  "label": "Heat Set Insert",  "group": "3D Printing", "tol": -0.1},
            {"id": "lid",     "label": "Lid (Snug)",       "group": "3D Printing", "tol": 0.1},
            {"id": "slider",  "label": "Slider / Moving",  "group": "3D Printing", "tol": 0.25},
            
            # Mechanical / CNC (Tighter)
            {"id": "iso_h7",  "label": "ISO H7 (Sliding)", "group": "Mechanical",  "tol": 0.012},
            {"id": "iso_p7",  "label": "ISO P7 (Press)",   "group": "Mechanical",  "tol": -0.015},
            {"id": "cnc_clr", "label": "CNC Clearance",    "group": "Mechanical",  "tol": 0.1}
        ]

    def load_fits(self) -> dict:
        """
        Loads all fits.
        Returns a dict: { 'groups': [...], 'custom': [...] }
        Handles migration of legacy flat files.
        """
        defaults = self.get_defaults()
        user_data = self._read_json()
        
        # Data Structure V2: { "overrides": {id: tol}, "custom": [{id, label, group, tol}] }
        
        # MIGRATION: Convert old flat dict to new structure
        if user_data and not ('overrides' in user_data or 'custom' in user_data):
            # It's an old file! {"bolt": 0.3}
            migrated = {"overrides": {}, "custom": []}
            known_ids = [d['id'] for d in defaults]
            
            for k, v in user_data.items():
                if k in known_ids:
                    migrated['overrides'][k] = float(v)
                else:
                    # Treat unknown keys as custom fits (generic)
                    migrated['custom'].append({
                        "id": k, 
                        "label": k.capitalize(), 
                        "group": "Custom", 
                        "tol": float(v)
                    })
            user_data = migrated
            # Auto-save migration? better wait for explicit save to avoid unwanted writes
            
        overrides = user_data.get('overrides', {})
        customs = user_data.get('custom', [])
        
        # 1. Apply Overrides to Defaults
        final_defaults = []
        for d in defaults:
            new_fit = d.copy()
            if d['id'] in overrides:
                new_fit['tol'] = overrides[d['id']]
            final_defaults.append(new_fit)
            
        # 2. Return payload
        return {
            "standards": final_defaults,
            "customs": customs
        }

    def save_fits(self, payload: dict) -> bool:
        """
        Saves user customizations.
        Expected payload: { "overrides": {...}, "custom": [...] }
        """
        try:
            # Validate structure lightly
            data = {
                "overrides": payload.get('overrides', {}),
                "custom": payload.get('custom', [])
            }
            self._write_json(data)
            return True
        except: return False
