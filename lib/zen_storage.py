import adsk.core, adsk.fusion
import traceback
from .zen_utils import log_diag

GROUP_NAME = "ZenParams"

class ZenStorage:
    """
    Handles robust data persistence using Fusion 360 Attributes.
    Stores data directly in the Design object, making it portable with the .f3d file.
    """
    
    def __init__(self, design):
        self.design = design
        
    def set(self, key, value):
        """Save a string value to attributes."""
        try:
            if not self.design: return False
            self.design.attributes.add(GROUP_NAME, key, str(value))
            return True
        except:
            return False
            
    def get(self, key, default=None):
        """Retrieve a string value from attributes."""
        try:
            if not self.design: return default
            attr = self.design.attributes.itemByName(GROUP_NAME, key)
            if attr:
                return attr.value
            return default
        except:
            return default

    def delete(self, key):
        """Remove a specific attribute."""
        try:
            if not self.design: return
            attr = self.design.attributes.itemByName(GROUP_NAME, key)
            if attr:
                attr.deleteMe()
        except: pass

    @staticmethod
    def get_current_preset_name(design):
        """Static helper for quick access."""
        try:
            attr = design.attributes.itemByName(GROUP_NAME, "current_preset")
            if attr: return attr.value
            
            # FALLBACK: Check for legacy parameter
            p_legacy = design.userParameters.itemByName('_zen_current_preset')
            if p_legacy:
                val = p_legacy.comment
                # Auto-migrate? Maybe not yet.
                return val
            
            return None
        except:
            return None
