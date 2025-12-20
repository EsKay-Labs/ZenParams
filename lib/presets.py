"""
ZenParams Preset Library
Values based on ISO 2768-m standards and common manufacturing best practices.
"""

PRESETS = {
    "3D Print (Tight Fit)": {
        "clearance": "0.1 mm",
        "hole_compensation": "0.15 mm",
        "press_fit_offset": "0.05 mm"
    },
    "3D Print (Loose Fit)": {
        "clearance": "0.4 mm",
        "sliding_gap": "0.5 mm",
        "layer_height": "0.2 mm"
    },
    "3D Print (Balanced)": {
        "clearance": "0.25 mm",
        "press_fit_offset": "0.1 mm"
    },
    "Woodworking (Premium)": {
        "joint_clearance": "0.4 mm", # Allows for glue swell
        "dado_oversize": "0.2 mm",
        "plywood_nominal": "18 mm"
    },
    "Woodworking (Rough/Field)": {
        "joint_clearance": "0.8 mm",
        "expansion_gap": "2.0 mm"
    },
    "CNC (Standard - 5 thou)": {
        "tolerance": "0.127 mm", # +/- 0.005 inch
        "finish_pass": "0.25 mm"
    },
    "CNC (Precision)": {
        "tolerance": "0.02 mm", # H7/h7 range
        "bearing_fit": "0.01 mm"
    }
}

def get_presets():
    """Returns the dictionary of available presets."""
    return PRESETS
