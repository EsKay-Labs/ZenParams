import adsk.core
import adsk.fusion
import traceback
import os
import sys
import time

# Ensure local lib directory is in path
APP_PATH = os.path.dirname(os.path.abspath(__file__))
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)

# Global variables to hold event handlers to keep them referenced
_handlers = []
_app = None
_ui = None
_palette = None
_initial_data_sent = False

CMD_ID = 'zenparams_cmd_v2'
PALETTE_ID = 'zenparams_palette_v8'  # Changed to force new instance with v11 HTML
PALETTE_URL = './ui/index.html'

def run(context):
    """Entry point for the ZenParams Add-In.

    Sets up the user interface, registers commands, and initializes the Palette.
    """
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        
        # CLEANUP: Remove old bridge file to force fresh sync
        bridge_file = os.path.join(APP_PATH, 'ui', 'data_bridge.json')
        if os.path.exists(bridge_file):
            try:
                os.remove(bridge_file)
            except:
                pass
        
        # PREVENT SCRIPT FROM STOPPING AUTOMATICALLY
        # Moved to top to ensure it registered before any potential errors
        adsk.autoTerminate(False)
        
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
            
        # Create or Get Palette (Non-Destructive)
        palette = _ui.palettes.itemById(PALETTE_ID)
        if not palette:
            palette = _ui.palettes.add(PALETTE_ID, 'ZenParams V11', 'ui/zenparams_v11.html', True, True, True, 300, 600)
            try:
                palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
            except:
                pass  # Docking can fail during startup, just continue floating
            
        _palette = palette

        # Connect HTML Event Handler (Safe Add)
        on_html_event = MyHTMLEventHandler()
        palette.incomingFromHTML.add(on_html_event)
        _handlers.append(on_html_event)
            
        # Startup Visibility
        if _app.isStartupComplete:
            if not palette.isVisible:
                 show_palette()
            # FIRST DOC FIX: Send initial data for the already-open document
            # Add small delay to allow HTML page to fully load
            try:
                import time
                time.sleep(0.5)  # Wait 500ms for HTML to initialize
                adsk.doEvents()  # Process any pending events
                on_html_event.send_initial_data()
            except:
                pass
        else:
            on_startup_completed = StartupCompletedHandler()
            _app.startupCompleted.add(on_startup_completed)
            _handlers.append(on_startup_completed)
            
        # Connect to Document Activated Event (Auto-Refresh)
        on_document_activated = DocumentActivatedHandler()
        _app.documentActivated.add(on_document_activated)
        _handlers.append(on_document_activated)
        
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
    global _ui, _cmd_def, _palette, _handlers
    
    # Kill Zombies
    _handlers = []
    
    try:
        # Clean up palette
        _palette = _ui.palettes.itemById(PALETTE_ID)
        if _palette:
            # NON-DESTRUCTIVE: Keep palette open
            pass
            # _palette.deleteMe()
            
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
    
    # DEBUG: Reveal running location (Moved to guaranteed path)
    if _ui:
        pass
        # _ui.messageBox(f"Startup ZenParams v6.0 from:\n{os.path.dirname(__file__)}")
    
    _palette = _ui.palettes.itemById(PALETTE_ID)
    if not _palette:
        # Use absolute path to bypass caching, ensuring forward slashes for URL
        html_path = os.path.join(APP_PATH, 'ui', 'zenparams_v10.html') # v10
        html_file_url = html_path.replace('\\', '/')
        if not html_file_url.startswith('file:///'):
             # Ensure connection is correct for local file
             if not html_file_url.startswith('/'):
                 html_file_url = '/' + html_file_url
             html_file_url = 'file://' + html_file_url
        
        _palette = _ui.palettes.add(
            PALETTE_ID, 
            'ZenParams v10', 
            html_file_url, 
            True, # is visible
            True, # close button
            True, # is resizable
            400,  # width (increased)
            600   # height (increased)
        )
        
        # _ui.messageBox("Palette Created")

        # Snap to Right (Requested Feature)
        try:
             _palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
        except:
             # Docking can fail on startup if UI isn't ready. Fail safe to floating.
             pass
             
        # _ui.messageBox("Docking Attempted")
        # _palette.isVisible = True # Removed: Rely on palettes.add(..., True, ...) to avoid startup crash
    else:
        _palette.isVisible = True

    # Connect to HTML event
    on_html_event = MyHTMLEventHandler()
    _palette.incomingFromHTML.add(on_html_event)
    _handlers.append(on_html_event) # Keep usage reference
    
    # GHOST PROTECTION: We do NOT call send_initial_data here.
    # The DocumentActivatedHandler will populate the bridge file on actual tab switch.
    # User actions (Load, Save, etc.) will also update it.
    # This prevents the "Ghost Caller" (run -> show_palette) from wiping valid data.

class StartupCompletedHandler(adsk.core.ApplicationEventHandler):
    def notify(self, args):
        try:
             # Once startup is complete, show the palette
             show_palette()
        except:
             if _ui:
                 _ui.messageBox('Startup Handler Failed:\n{}'.format(traceback.format_exc()))

# Global state to prevent spurious refreshes on same document
_last_active_doc_name = None

class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
    def notify(self, args):
        global _last_active_doc_name
        try:
            # Helper to log
            def log_diag(msg):
                try:
                    app = adsk.core.Application.get()
                    app.userInterface.palettes.itemById('TextCommands').writeText(f"[ZenParams] {msg}")
                except: pass

            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            current_doc_name = ""
            current_doc_id = ""
            param_count = 0
            
            if design and design.parentDocument:
                current_doc_name = design.parentDocument.name
                try:
                    # Use creationId for unique identification (or hash the object as fallback)
                    current_doc_id = design.parentDocument.creationId
                except:
                    try:
                        # Fallback: use object id (memory address)
                        current_doc_id = str(id(design.parentDocument))
                    except:
                        current_doc_id = current_doc_name  # Last resort
                try:
                    param_count = design.userParameters.count
                except: pass
            
            log_diag(f"[DIAG] DocActivated: '{current_doc_name}' ID={current_doc_id[:8] if current_doc_id else 'None'}... Count={param_count} Last: '{_last_active_doc_name}'")
            
            # Debounce: If document ID hasn't changed, ignore this event
            # Using ID instead of name because multiple docs can be named "Untitled"
            if _last_active_doc_name == current_doc_id:
                log_diag(f"[DIAG] Debounce BLOCKED refresh.")
                return
                
            _last_active_doc_name = current_doc_id
             
            # Document has changed - refresh the UI
            # Ghost Protection removed here - legitimate empty docs need to refresh
            # The protection in send_initial_data handles the edge cases
            temp_handler = MyHTMLEventHandler()
            temp_handler.send_initial_data()
        except:
             pass

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    """Handles the CommandCreated event to open the Palette."""
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            
            show_palette()
        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

import json
import importlib
from lib.param_parser import ParamParser
import lib.presets as presets_lib 
# Force reload to clear old cached values
importlib.reload(presets_lib)
from lib.presets import get_presets

class MyHTMLEventHandler(adsk.core.HTMLEventHandler):
    """Handles messages coming from the HTML Palette."""
    def notify(self, args):
        try:
            # _ui.messageBox(f"Received: {args.data}") # DEBUG PROBE
            html_args = json.loads(args.data)
            action = html_args.get('action')
            data = html_args.get('data')
            
            # TELEMETRY: Write to Text Commands Palette
            if action:
                self.log_to_console(f"Action Received: {action}")
            else:
                self.log_to_console(f"Action None! Raw Data: {args.data}")
            
            if action == 'check': 
                pass
            elif action == 'create_param':
                self.handle_create_param(data)
            elif action == 'get_initial_data':
                self.log_to_console("Processing get_initial_data...")
                self.send_initial_data()
            elif action == 'batch_update':
                self.handle_batch_update(data)
            elif action == 'save_preset':
                self.log_to_console("Processing save_preset...")
                self.handle_save_preset(data)
            elif action == 'delete_preset':
                self.log_to_console("Processing delete_preset...")
                self.handle_delete_preset(data)
            elif action == 'set_current_preset':
                self.log_to_console("Processing set_current_preset...")
                self.handle_set_current_preset(data)
            elif action == 'refresh':
                self.send_all_params()
                
        except:
            _ui.messageBox('Failed handling HTML event:\n{}'.format(traceback.format_exc()))

    def handle_batch_update(self, updates):
        """Handles bulk updates from the UI table."""
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
             self.send_response("No active design.", "error")
             return

        count = 0
        errors = []
        
        try:
            for item in updates:
                name = item.get('name')
                expr = item.get('expression')
                cmt = item.get('comment')
                
                # Basic validation
                if not name or not expr: continue
                
                try:
                    existing = design.userParameters.itemByName(name)
                    if existing:
                        if existing.expression != expr:
                            existing.expression = expr
                        if cmt and existing.comment != cmt:
                            existing.comment = cmt
                        count += 1
                    else:
                        val_input = adsk.core.ValueInput.createByString(expr)
                        
                        # Creation Strategy: mm -> (unitless/default) -> Fail
                        created = False
                        
                        # Strategy 1: Millimeters (Standard)
                        if not created:
                            try:
                                design.userParameters.add(name, val_input, "mm", cmt or "")
                                created = True
                                count += 1
                            except: pass
                            
                        # Strategy 2: Unitless / Default (Fallback)
                        if not created:
                            try:
                                design.userParameters.add(name, val_input, "", cmt or "")
                                created = True
                                count += 1
                            except: pass
                            
                        if not created:
                             errors.append(f"{name}: Failed to create (check units/format)")

                except Exception as e_outer:
                     errors.append(f"{name}: {str(e_outer)}")

            if errors:
                self.send_response(f"Refreshed. Skipped {len(errors)} errors.", "error")
            else:
                self.send_response(f"Updated {count} parameters.", "success")
            
            # Allow Fusion to catch up before reading back
            adsk.doEvents()
            
            self.send_all_params() # Refresh table source of truth
            
        except Exception as e:
            self.send_response(f"Batch Error: {e}", "error")
    
    def handle_set_current_preset(self, data):
        """Stores current preset name in Fusion parameter for persistence."""
        preset_name = data.get('name')
        
        self.log_to_console(f"[DEBUG] Saving current preset: {preset_name}")
        
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            return
        
        try:
            param_name = '_zen_current_preset'
            existing_param = None
            
            for param in design.userParameters:
                if param.name == param_name:
                    existing_param = param
                    break
            
            if preset_name:
                # Store preset name in comment field (not expression)
                if existing_param:
                    existing_param.comment = preset_name
                else:
                    # Create dummy parameter with preset name in comment
                    design.userParameters.add(param_name, adsk.core.ValueInput.createByString('1'), '', preset_name)
            else:
                # Clear parameter if None
                if existing_param:
                    existing_param.deleteMe()
                    
            # CRITICAL: Wait for Fusion to commit, then send fresh data
            # This beats the Ghost by writing correct data AFTER the external trigger
            adsk.doEvents()
            self.send_initial_data()
            
        except Exception as e:
            self.log_to_console(f"Set preset error: {e}")


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
    
    def handle_delete_preset(self, data):
        """Deletes a user preset from user_presets.json."""
        name = data.get('name')
        
        if not name:
            self.send_response("No preset name provided.", "error")
            return
            
        json_path = os.path.join(APP_PATH, 'user_presets.json')
        
        try:
            # Load existing
            current_presets = {}
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        current_presets = json.load(f)
                    except: pass
            
            # Check if preset exists
            if name not in current_presets:
                self.send_response(f"Preset '{name}' not found.", "error")
                return
            
            # Delete
            del current_presets[name]
            
            # Save
            with open(json_path, 'w') as f:
                json.dump(current_presets, f, indent=4)
                
            self.send_response(f"Preset '{name}' deleted.", "success")
            
            # Refresh Lists
            self.send_initial_data()
            
        except Exception as e:
            self.send_response(f"Delete Failed: {e}", "error")


    def send_initial_data(self):
        """Sends merged presets (Factory + User) to UI."""
        # DIAGNOSTIC: Trace who is calling this
        try:
             stack = "".join(traceback.format_stack())
             if "DocumentActivatedHandler" not in stack and "handle_set_current_preset" not in stack and "handle_save_preset" not in stack:
                  self.log_to_console(f"[DIAG] Ghost Caller Trace:\n{stack}")
        except: pass

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
        
        # 3. Fetch Params immediately
        param_data = self.get_param_list()
        
        # 4. Detect current preset from Fusion parameter
        current_preset = None
        has_legacy_params = False
        
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design:
                for param in design.userParameters:
                    if param.name == '_zen_current_preset':
                        # Read preset name from comment field
                        current_preset = param.comment
                        break
                
                # Legacy Detection (No ZenPreset but has params)
                if not current_preset and design.userParameters.count > 0:
                     # Filter out our own param if it exists but is empty
                     real_params = [p for p in design.userParameters if p.name != '_zen_current_preset']
                     if len(real_params) > 0:
                         has_legacy_params = True
                         
        except:
            pass
        
        self.log_to_console(f"[DEBUG] Current: {current_preset} Legacy: {has_legacy_params}")
        
        # GHOST PROTECTION: If we're about to send 0 params, check if bridge file has valid data
        # If it does, DON'T overwrite (we're probably in a stale API state from script restart)
        if len(param_data) == 0:
            try:
                bridge_path = os.path.join(APP_PATH, 'ui', 'data_bridge.json')
                if os.path.exists(bridge_path):
                    with open(bridge_path, 'r') as f:
                        existing = json.load(f)
                        if existing.get('params') and len(existing.get('params', [])) > 0:
                            self.log_to_console("[GHOST PROTECTION] Blocked overwrite of valid data with empty data!")
                            return  # DON'T SEND - preserve existing data
            except:
                pass
        
        # 5. Atomic Send
        payload = {
            'presets': all_presets,
            'params': param_data,
            'current_preset': current_preset,
            'legacy_params': has_legacy_params
        }
        
        self.log_to_console(f"Sending ATOMIC Payload. Presets: {len(all_presets)} Params: {len(param_data)}")
        self.send_response(payload, 'init_all')

    def get_param_list(self):
        """Helper to get param list without sending it."""
        try:
            app = adsk.core.Application.get()
            product = app.activeProduct
            self.log_to_console(f"[DIAG] Active Product: {product.productType if product else 'None'}")
            
            design = adsk.fusion.Design.cast(product)
            if not design: 
                self.log_to_console("[DIAG] FAIL: Could not cast to Design.")
                return []
                
            try:
                doc_name = design.parentDocument.name
                self.log_to_console(f"[DIAG] Document: {doc_name}")
            except:
                self.log_to_console("[DIAG] Document: Unknown")

            param_list = []
            
            # DEBUG LOG
            try:
                count = design.userParameters.count
                self.log_to_console(f"[DIAG] design.userParameters.count = {count}")
            except Exception as e:
                self.log_to_console(f"[DIAG] FAIL: Could not count params: {e}")

            # 1. User Parameters
            for param in design.userParameters:
                try:
                    # Filter internal param
                    if param.name == '_zen_current_preset': continue
                    
                    # self.log_to_console(f"[DIAG] Processing: {param.name}")
                    
                    param_list.append({
                        'name': param.name,
                        'expression': param.expression,
                        'value': param.value,
                        'unit': param.unit,
                        'comment': param.comment,
                        'isUser': True
                    })
                except Exception as e_item:
                    self.log_to_console(f"[WARN] Failed to read param {param.name if param else '?'}: {str(e_item)}")
                    continue
        except Exception as e_main:
             self.log_to_console(f"[CRITICAL] get_param_list crashed: {e_main}")
             return []
            
        # 2. Model Params (Limit 50)
        count = 0
        for param in design.allParameters:
            if count > 50: break
            # Skip if explicitly a user parameter (already added)
            if design.userParameters.itemByName(param.name): continue
            
            param_list.append({
                'name': param.name,
                'expression': param.expression,
                'value': param.value,
                'unit': param.unit,
                'comment': param.comment,
                'isUser': False
            })
            count += 1
            
        return param_list

    def send_all_params(self):
        """Fetches all params (User + Model) and sends to UI."""
        param_list = self.get_param_list()
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
            if status in ['init_presets', 'update_table', 'init_all']:
                 data = json.dumps({'content': message, 'type': status, 'timestamp': time.time()})
            else:
            # Standard status message
                 data = json.dumps({'message': message, 'status': status, 'type': 'notification', 'timestamp': time.time()})
            
            self.log_to_console(f"Sending Payload [{status}] Len: {len(data)}")
            
            # Use Fusion's native HTML communication
            try:
                palette.sendInfoToHTML('response', data)
                self.log_to_console(f"Sent via sendInfoToHTML")
            except Exception as e:
                self.log_to_console(f"sendInfoToHTML error: {e}")

    def log_to_console(self, msg):
        """Writes to the Fusion 360 Text Commands palette."""
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            cmd_palette = ui.palettes.itemById('TextCommands')
            if cmd_palette:
                cmd_palette.writeText(f"[ZenParams] {msg}")
        except:
            pass
