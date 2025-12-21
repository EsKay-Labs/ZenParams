import adsk.core
import adsk.fusion
import traceback
import os
import sys
import time
import json

# Ensure local lib directory is in path (Kept for future proofing, though lib is gone)
APP_PATH = os.path.dirname(os.path.abspath(__file__))
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)

# Global variables
_handlers = []
_app = None
_ui = None
_palette = None
_last_active_doc_name = None # For polling debounce

CMD_ID = 'zenparams_cmd_v2'
PALETTE_ID = 'zenparams_palette_v8'
PALETTE_URL = './ui/index.html'

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def get_presets():
    """Returns built-in factory presets (3D Printing Design Specs)."""
    return {
        "3DP Standard": {
            "WallThick": "1.2 mm", 
            "Clearance": "0.2 mm",
            "HoleComp": "0.15 mm",
            "FilletSm": "1 mm"
        },
        "3DP Precision": {
            "WallThick": "0.8 mm", 
            "Clearance": "0.1 mm", 
            "HoleComp": "0.1 mm",
            "PressFit": "0.05 mm"
        },
        "3DP Structural": {
            "WallThick": "2.4 mm", 
            "Clearance": "0.35 mm",
            "RibThick": "1.6 mm",
            "MinFeature": "0.8 mm"
        }
    }

def log_diag(msg):
    """Writes to the Fusion 360 Text Commands palette."""
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        cmd_palette = ui.palettes.itemById('TextCommands')
        if cmd_palette:
            cmd_palette.writeText(f"[ZenParams] {msg}")
    except:
        pass

def show_palette():
    """Validates and displays the ZenParams palette."""
    global _ui, _palette, _handlers
    
    _palette = _ui.palettes.itemById(PALETTE_ID)
    if not _palette:
        # Use absolute path
        html_path = os.path.join(APP_PATH, 'ui', 'index.html')
        html_file_url = html_path.replace('\\', '/')
        if not html_file_url.startswith('file:///'):
             if not html_file_url.startswith('/'):
                 html_file_url = '/' + html_file_url
             html_file_url = 'file://' + html_file_url
        
        _palette = _ui.palettes.add(
            PALETTE_ID, 
            'ZenParams Pro', 
            html_file_url, 
            True, True, True, 400, 600
        )
        
        # Snap to Right
        try:
             _palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
        except:
             pass
    else:
        _palette.isVisible = True

    # Connect to HTML event
    on_html_event = MyHTMLEventHandler()
    _palette.incomingFromHTML.add(on_html_event)
    _handlers.append(on_html_event)


# -----------------------------------------------------------------------------
# EVENT HANDLERS
# -----------------------------------------------------------------------------

class StartupCompletedHandler(adsk.core.ApplicationEventHandler):
    def notify(self, args):
        try:
             show_palette()
        except:
             if _ui:
                 _ui.messageBox('Startup Handler Failed:\n{}'.format(traceback.format_exc()))

class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
    def notify(self, args):
        global _last_active_doc_name
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            current_doc_id = ""
            
            if design and design.parentDocument:
                try:
                    current_doc_id = design.parentDocument.creationId
                except:
                    current_doc_id = design.parentDocument.name

            # Debounce
            if _last_active_doc_name == current_doc_id:
                return
            _last_active_doc_name = current_doc_id
             
            # Refresh UI
            temp_handler = MyHTMLEventHandler()
            temp_handler.send_initial_data()
        except:
             pass

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            show_palette()
        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class MyHTMLEventHandler(adsk.core.HTMLEventHandler):
    """Handles messages coming from the HTML Palette."""
    
    def log_to_console(self, msg):
        log_diag(msg)
        
    def notify(self, args):
        try:
            html_args = json.loads(args.data)
            action = html_args.get('action')
            data = html_args.get('data')
            
            # log_diag(f"Action: {action}")

            if action == 'get_active_doc_info':
                active_doc_info = self.get_active_doc_info_json()
                args.returnData = active_doc_info
            elif action == 'get_initial_data':
                response_data = self.build_initial_data()
                args.returnData = response_data
            elif action == 'batch_update':
                self.handle_batch_update(data)
            elif action == 'save_preset':
                self.handle_save_preset(data)
            elif action == 'delete_preset':
                self.handle_delete_preset(data)
            elif action == 'set_current_preset':
                self.handle_set_current_preset(data)
            elif action == 'delete_param':
                self.handle_delete_param(data, args)
            elif action == 'refresh':
                self.send_all_params()
                
        except:
            if _ui: _ui.messageBox('Event Error:\n{}'.format(traceback.format_exc()))

    def send_response(self, message, status):
        """Sends data back to Palette."""
        palette = _ui.palettes.itemById(PALETTE_ID)
        if palette:
            if status in ['init_presets', 'update_table', 'init_all']:
                 data = json.dumps({'content': message, 'type': status, 'timestamp': time.time()})
            else:
                 data = json.dumps({'message': message, 'status': status, 'type': 'notification', 'timestamp': time.time()})
            
            try:
                palette.sendInfoToHTML('response', data)
            except: pass

    # --- ACTION HANDLERS ---

    def handle_delete_param(self, data, args):
        param_name = data.get('name')
        if not param_name:
            args.returnData = json.dumps({'status': 'error', 'msg': 'No name'})
            return

        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design: 
                args.returnData = json.dumps({'status': 'error', 'msg': 'No design'})
                return
            
            param = design.userParameters.itemByName(param_name)
            if not param:
                args.returnData = json.dumps({'status': 'success', 'msg': 'Already deleted'})
                return
            
            param.deleteMe()
            args.returnData = json.dumps({'status': 'success', 'msg': f"Deleted {param_name}"})
            
        except Exception as e:
            msg = str(e)
            if "dependency" in msg.lower() or "refer" in msg.lower():
                final_msg = f"Cannot delete '{param_name}': Used in design."
            else:
                final_msg = f"Delete failed: {msg}"
            
            args.returnData = json.dumps({'status': 'error', 'msg': final_msg})

    def handle_batch_update(self, updates):
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design: return

        count = 0
        errors = []
        
        try:
            for item in updates:
                name = item.get('name')
                expr = item.get('expression')
                cmt = item.get('comment')
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
                        try:
                            design.userParameters.add(name, val_input, "mm", cmt or "")
                            count += 1
                        except:
                            try:
                                design.userParameters.add(name, val_input, "", cmt or "")
                                count += 1
                            except Exception as e:
                                errors.append(f"{name}: {e}")
                except:
                     pass

            if errors:
                self.send_response(f"Refreshed. {len(errors)} errors.", "error")
            else:
                self.send_response(f"Updated {count}.", "success")
            
            adsk.doEvents()
            self.send_all_params()
            
        except Exception as e:
            self.send_response(f"Batch Error: {e}", "error")

    def handle_set_current_preset(self, data):
        preset_name = data.get('name')
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design: return
        
        try:
            param_name = '_zen_current_preset'
            existing = design.userParameters.itemByName(param_name)
            
            if preset_name:
                if existing:
                    existing.comment = preset_name
                else:
                    design.userParameters.add(param_name, adsk.core.ValueInput.createByString('1'), '', preset_name)
            else:
                if existing: existing.deleteMe()
                    
            adsk.doEvents()
            self.send_initial_data()
        except: pass

    def handle_save_preset(self, data):
        name = data.get('name')
        params = data.get('params')
        
        if not name or not params: return
            
        json_path = os.path.join(APP_PATH, 'user_presets.json')
        try:
            current = {}
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try: current = json.load(f)
                    except: pass
            
            current[name] = params
            with open(json_path, 'w') as f:
                json.dump(current, f, indent=4)
                
            self.send_response(f"Saved '{name}'!", "success")
            self.handle_set_current_preset({'name': name})
            
        except Exception as e:
            self.send_response(f"Save Failed: {e}", "error")

    def handle_delete_preset(self, data):
        name = data.get('name')
        json_path = os.path.join(APP_PATH, 'user_presets.json')
        try:
            current = {}
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try: current = json.load(f)
                    except: pass
            
            if name in current:
                del current[name]
                with open(json_path, 'w') as f:
                    json.dump(current, f, indent=4)
                self.send_response(f"Deleted '{name}'", "success")
                self.send_initial_data()
        except Exception as e:
             self.send_response(f"Delete Error", "error")

    # --- DATA FETCHERS ---

    def get_param_list(self):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design: return []
            
            param_list = []
            
            # User Params
            for param in design.userParameters:
                if param.name == '_zen_current_preset': continue
                param_list.append({
                    'name': param.name,
                    'expression': param.expression,
                    'unit': param.unit,
                    'comment': param.comment,
                    'isUser': True
                })
            
            # Model Params (Limit 50)
            count = 0
            for param in design.allParameters:
                if count > 50: break
                if design.userParameters.itemByName(param.name): continue
                param_list.append({
                    'name': param.name,
                    'expression': param.expression,
                    'unit': param.unit,
                    'comment': param.comment,
                    'isUser': False
                })
                count += 1
                
            return param_list
        except:
            return []

    def get_active_doc_info_json(self):
        doc_id = ""
        doc_name = ""
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design and design.parentDocument:
                doc_name = design.parentDocument.name
                try: doc_id = design.parentDocument.creationId
                except: doc_id = doc_name
        except: pass
        return json.dumps({'name': doc_name, 'id': doc_id})

    def build_initial_data(self):
        payload = self._gather_payload_dict()
        return json.dumps({'content': payload, 'type': 'init_all'})

    def send_initial_data(self):
        payload = self._gather_payload_dict()
        self.send_response(payload, 'init_all')
        
    def send_all_params(self):
        pl = self.get_param_list()
        self.send_response(pl, 'update_table')

    def _gather_payload_dict(self):
        # 1. Presets
        all_presets = get_presets().copy()
        json_path = os.path.join(APP_PATH, 'user_presets.json')
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    all_presets.update(json.load(f))
            except: pass
            
        # 2. Params
        param_data = self.get_param_list()
        
        # 3. Current State
        current_preset = None
        has_legacy = False
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design:
                p = design.userParameters.itemByName('_zen_current_preset')
                if p: current_preset = p.comment
                
                # Check legacy
                if not current_preset and design.userParameters.count > 0:
                     real = [x for x in design.userParameters if x.name != '_zen_current_preset']
                     if len(real) > 0: has_legacy = True
        except: pass
        
        return {
            'presets': all_presets,
            'params': param_data,
            'current_preset': current_preset,
            'legacy_params': has_legacy
        }


# -----------------------------------------------------------------------------
# MAIN ENTRY POINTS
# -----------------------------------------------------------------------------

def run(context):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        adsk.autoTerminate(False)
        
        # Add Command
        cmd_def = _ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def: cmd_def.deleteMe()
        cmd_def = _ui.commandDefinitions.addButtonDefinition(
            CMD_ID, 'ZenParams Pro', 'Open ZenParams Palette', './resources'
        )
        
        on_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)
        
        # Toolbar
        panel = _ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        if panel:
            panel.controls.addCommand(cmd_def)
            
        # Check Palettes
        palette = _ui.palettes.itemById(PALETTE_ID)
        if palette: palette.deleteMe() # Force refresh on load
        
        show_palette()
        
        # Startup Handler
        if not _app.isStartupComplete:
            on_start = StartupCompletedHandler()
            _app.startupCompleted.add(on_start)
            _handlers.append(on_start)
            
        # Doc Handler
        on_doc = DocumentActivatedHandler()
        _app.documentActivated.add(on_doc)
        _handlers.append(on_doc)
        
        adsk.autoTerminate(False)
        
    except:
        if _ui: _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    global _ui, _palette
    try:
        palette = _ui.palettes.itemById(PALETTE_ID)
        if palette: palette.deleteMe()
        
        cmd = _ui.commandDefinitions.itemById(CMD_ID)
        if cmd: cmd.deleteMe()
        
        panel = _ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        if panel:
            c = panel.controls.itemById(CMD_ID)
            if c: c.deleteMe()
            
    except:
        pass
