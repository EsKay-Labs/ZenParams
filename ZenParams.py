import adsk.core
import adsk.fusion
import traceback
import os
import sys

# Ensure local lib directory is in path
APP_PATH = os.path.dirname(os.path.abspath(__file__))
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)

# Global variables to hold event handlers to keep them referenced
_handlers = []
_app = None
_ui = None
_palette = None

CMD_ID = 'zenparams_cmd_v2'
PALETTE_ID = 'zenparams_palette_v3'
PALETTE_URL = './ui/index.html'

def run(context):
    """Entry point for the ZenParams Add-In.

    Sets up the user interface, registers commands, and initializes the Palette.
    """
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        
        # DEBUG: Confirm script is loading
        _ui.messageBox('ZenParams Loading...') 
        
        # Create the command definition
        cmd_def = _ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            cmd_def.deleteMe()
            
        cmd_def = _ui.commandDefinitions.addButtonDefinition(
            CMD_ID, 
            'ZenParams Console', 
            'Open the ZenParams floating console.',
            './resources'
        )
        
        # Connect to the command created event
        on_command_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_command_created)
        _handlers.append(on_command_created)
        
        # 1. Guaranteed Location: Scripts/Add-Ins Panel
        addins_panel = _ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        if addins_panel:
            cntrl = addins_panel.controls.itemById(CMD_ID)
            if cntrl: cntrl.deleteMe()
            addins_panel.controls.addCommand(cmd_def)
            
        # 2. Preferred Location: Modify Toolbar (Best Effort)
        try:
            target_panel = _ui.allToolbarPanels.itemById('SolidModifyPanel')
            if target_panel:
                cntrl = target_panel.controls.itemById(CMD_ID)
                if cntrl: cntrl.deleteMe()
                target_panel.controls.addCommand(cmd_def)
        except:
            pass # Fail silently for toolbar, but Scripts panel is safe
            
        # Register palette event handler if palette exists (re-run scenario)
        palette = _ui.palettes.itemById(PALETTE_ID)
        if palette:
            palette.deleteMe() # Re-create to ensure clean state
            
        # Only show on specific request or first run if desired, 
        # but for an Add-In, we usually wait for the button press.
        # However, to confirm it's working for the user now:
        show_palette()
        
        # PREVENT SCRIPT FROM STOPPING AUTOMATICALLY
        # This is critical for Event Handlers to persist
        adsk.autoTerminate(False)
        
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    """Exit point for the ZenParams Add-In.

    Cleans up the user interface and unregisters commands.
    """
    global _ui, _palette, _handlers
    try:
        # Clean up palette
        _palette = _ui.palettes.itemById(PALETTE_ID)
        if _palette:
            _palette.deleteMe()
            
        # Clean up UI controls from Modify Panel
        target_panel = _ui.allToolbarPanels.itemById('SolidModifyPanel')
        if target_panel:
            cntrl = target_panel.controls.itemById(CMD_ID)
            if cntrl:
                cntrl.deleteMe()

        # Also check old location just in case
        addins_panel = _ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        if addins_panel:
            cntrl = addins_panel.controls.itemById(CMD_ID)
            if cntrl:
                cntrl.deleteMe()
                
        # Clean up command definition
        cmd_def = _ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            cmd_def.deleteMe()
            
        # Clear handlers
        _handlers = []
            
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def show_palette():
    """Validates and displays the ZenParams palette."""
    global _ui, _palette, _handlers
    
    _palette = _ui.palettes.itemById(PALETTE_ID)
    if not _palette:
        # Use absolute path to bypass caching, ensuring forward slashes for URL
        html_path = os.path.join(APP_PATH, 'ui', 'index.html')
        html_file_url = html_path.replace('\\', '/')
        if not html_file_url.startswith('file:///'):
             # Ensure connection is correct for local file
             if not html_file_url.startswith('/'):
                 html_file_url = '/' + html_file_url
             html_file_url = 'file://' + html_file_url
        
        _palette = _ui.palettes.add(
            PALETTE_ID, 
            'ZenParams v3', 
            html_file_url, 
            True, # is visible
            True, # close button
            True, # is resizable
            400,  # width (increased)
            600   # height (increased)
        )
        # _palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateFloating
    else:
        _palette.isVisible = True
        _palette.activate()

    # Connect to HTML event
    on_html_event = MyHTMLEventHandler()
    _palette.incomingFromHTML.add(on_html_event)
    _handlers.append(on_html_event) # Keep usage reference

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    """Handles the CommandCreated event to open the Palette."""
    def notify(self, args):
        try:
            show_palette()
        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

import json
from lib.param_parser import ParamParser
from lib.presets import get_presets

class MyHTMLEventHandler(adsk.core.HTMLEventHandler):
    """Handles messages coming from the HTML Palette."""
    def notify(self, args):
        try:
            html_args = json.loads(args.data)
            action = html_args.get('action')
            data = html_args.get('data')
            
            if action == 'create_param':
                self.handle_create_param(data)
            elif action == 'get_initial_data':
                self.send_initial_data()
            elif action == 'batch_update':
                self.handle_batch_update(data)
            elif action == 'refresh':
                self.send_all_params()
                
        except:
            _ui.messageBox('Failed handling HTML event:\n{}'.format(traceback.format_exc()))

            if errors:
                self.send_response(f"Updated {count}. Errors: {len(errors)}", "error")
            else:
                self.send_response(f"Batch updated {count} parameters.", "success")
                
            self.send_all_params() # Refresh table source of truth
            
        except Exception as e:
            self.send_response(f"Batch Error: {e}", "error")

    def handle_save_preset(self, data):
        """Saves a new custom preset to user_presets.json."""
        name = data.get('name')
        params = data.get('params') # Dict of name: expression
        
        if not name or not params:
            self.send_response("Invalid preset data.", "error")
            return
            
        json_path = os.path.join(APP_PATH, 'user_presets.json')
        
        try:
            # Load existing
            current_presets = {}
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        current_presets = json.load(f)
                    except: pass # Start fresh if corrupt
            
            # Update/Add
            current_presets[name] = params
            
            # Save
            with open(json_path, 'w') as f:
                json.dump(current_presets, f, indent=4)
                
            self.send_response(f"Template '{name}' saved!", "success")
            
            # Refresh Lists
            self.send_initial_data()
            
        except Exception as e:
            self.send_response(f"Save Failed: {e}", "error")

    def send_initial_data(self):
        """Sends merged presets (Factory + User) to UI."""
        # 1. Factory Presets
        all_presets = get_presets().copy()
        
        # 2. User Presets
        json_path = os.path.join(APP_PATH, 'user_presets.json')
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    user_presets = json.load(f)
                    all_presets.update(user_presets) # User overrides default if same name
            except:
                pass # Ignore load errors, just use defaults
                
        self.send_response({'presets': all_presets}, 'init_presets')
        self.send_all_params()
    def send_all_params(self):
        """Fetches all params (User + Model) and sends to UI."""
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            return

        param_list = []
        
        # 1. User Parameters (Editable)
        for param in design.userParameters:
            param_list.append({
                'name': param.name,
                'expression': param.expression,
                'value': param.value, # Internal value in cm
                'unit': param.unit,
                'comment': param.comment,
                'isUser': True
            })
            
        # 2. Model Parameters (Often Read-Only in this context, but useful to see)
        # Limiting to first 50 to avoid massive tables in complex designs
        count = 0
        for param in design.allParameters:
            if count > 50: break
            # Skip if it's already in user params
            if design.userParameters.itemByName(param.name):
                continue
                
            param_list.append({
                'name': param.name,
                'expression': param.expression,
                'value': param.value,
                'unit': param.unit,
                'comment': param.comment,
                'isUser': False
            })
            count += 1
        
        self.send_response(param_list, 'update_table')



    def handle_create_param(self, input_str):
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        
        if not design:
            self.send_response("No active design found.", "error")
            return

        parsed = ParamParser.parse(input_str)
        
        if 'error' in parsed:
            self.send_response(parsed['error'], "error")
            return
            
        try:
            # Check if parameter exists
            existing = design.userParameters.itemByName(parsed['name'])
            if existing:
                # Update existing
                existing.expression = parsed['expression']
                if parsed['comment']:
                    existing.comment = parsed['comment']
                self.send_response(f"Updated '{parsed['name']}' = {parsed['expression']}", "success")
            else:
                val_input = adsk.core.ValueInput.createByString(parsed['expression'])
                design.userParameters.add(parsed['name'], val_input, "mm", parsed['comment'])
                
                self.send_response(f"Created '{parsed['name']}' = {parsed['expression']}", "success")
            
            self.send_all_params() # Refresh table
                
        except Exception as e:
             self.send_response(f"Fusion Error: {str(e)}", "error")

    def send_response(self, message, status):
        """Sends a JSON response back to the Palette."""
        # Check if 'status' is a special key for data payload or a classic status string
        # To keep it simple, we wrap everything in 'message' if it's data, or use specific structure
        palette = _ui.palettes.itemById(PALETTE_ID)
        if palette:
            # If status is one of our data keys, we send raw data
            if status in ['init_presets', 'update_table']:
                 data = json.dumps({'content': message, 'type': status})
            else:
                 # Standard status message
                 data = json.dumps({'message': message, 'status': status, 'type': 'notification'})
                 
            palette.sendInfoToHTML('response', data)
