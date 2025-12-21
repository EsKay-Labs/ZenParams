"""
ZenParams Preset Library
Values based on ISO 2768-m standards and common manufacturing best practices.
"""

PRESETS = {
    "New Preset": {},
    "3D Print (Tight Fit)": {
        "clearance": "0.1 mm",
        "hole_compensation": "0.15 mm",
        "press_fit_offset": "0.05 mm"
    },
    "3D Print (Balanced)": {
        "clearance": "0.25 mm",
        "press_fit_offset": "0.1 mm",
        "layer_height": "0.2 mm"
    },
    "3D Print (Loose Fit)": {
        "clearance": "0.4 mm",
        "sliding_gap": "0.5 mm",
        "layer_height": "0.2 mm"
    }
}

def get_presets():
    """Returns the dictionary of available presets."""
    return PRESETS
