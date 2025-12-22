import adsk.core
import adsk.fusion
import json
import traceback
import time
import re
from .zen_utils import log_diag, PresetManager, FitManager
from .zen_crawler import ZenDependencyCrawler

class ZenPaletteEventHandler(adsk.core.HTMLEventHandler):
    """Handles messages coming from the HTML Palette."""
    
    def __init__(self, palette_id: str, root_path: str):
        super().__init__()
        self.palette_id = palette_id
        self.preset_manager = PresetManager(root_path)
        self.fit_manager = FitManager(root_path)

    def notify(self, args):
        try:
            # log_diag(f"Raw Event: {args.data}")
            if not args.data: return
            
            html_args = json.loads(args.data)
            action = html_args.get('action')

            if not action: return # Ignore heartbeats/empty events
            
            # Log only interesting events
            if action != 'get_active_doc_info':
                 log_diag(f"Action: {action}")
                 
            data = html_args.get('data')
            
            # Dispatcher
            dispatch_map = {
                'get_active_doc_info': self._handle_get_doc_info,
                'get_initial_data': self._handle_get_initial_data,
                'batch_update': self._handle_batch_update,
                'save_preset': self._handle_save_preset,
                'delete_preset': self._handle_delete_preset,
                'set_current_preset': self._handle_set_current_preset,
                'delete_param': self._handle_delete_param,
                'close_palette': self._handle_close_palette,
                'refresh': self._handle_refresh,
                'auto_sort': self._auto_sort_params,
                'save_fit_defaults': self._handle_save_fit_defaults
            }
            
            handler = dispatch_map.get(action)
            if handler:
                handler(data, args)
            else:
                log_diag(f"Unknown action: {action}")
                
        except Exception as e:
            self._send_error(f"Event Error: {str(e)}")
            log_diag(traceback.format_exc())

    # --- HANDLERS ---
    
    def _handle_save_fit_defaults(self, data, args):
        fits = data.get('fits')
        if not fits: return
        
        if self.fit_manager.save_fits(fits):
            self._send_notification("Fit Defaults Saved!", "success")
            # Resend all data to update UI state if needed
            self._send_initial_data()
        else:
            self._send_notification("Failed to save fits", "error")

    def _handle_get_doc_info(self, data, args):
        # ... (Existing Code)
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
        args.returnData = json.dumps({'name': doc_name, 'id': doc_id})

    def _handle_get_initial_data(self, data, args):
        payload = self._gather_payload_dict()
        args.returnData = json.dumps({'content': payload, 'type': 'init_all'})

    def _handle_refresh(self, data, args):
        self._send_all_params()

    def _handle_close_palette(self, data, args):
        app = adsk.core.Application.get()
        ui = app.userInterface
        palette = ui.palettes.itemById(self.palette_id)
        if palette:
            palette.isVisible = False

    def _handle_save_preset(self, data, args):
        name = data.get('name')
        params = data.get('params')
        if not name or not params: return
        
        if self.preset_manager.save_preset(name, params):
            self._send_notification(f"Saved '{name}'!", "success")
            self._handle_set_current_preset({'name': name}, None)
        else:
            self._send_notification("Save Failed", "error")

    def _handle_delete_preset(self, data, args):
        name = data.get('name')
        if self.preset_manager.delete_preset(name):
            self._send_notification(f"Deleted '{name}'", "success")
            self._send_initial_data()
        else:
            self._send_notification("Delete Failed", "error")

    def _handle_set_current_preset(self, data, args):
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
            self._send_initial_data()
        except: pass

    def _handle_delete_param(self, data, args):
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
            
            # Basic Dependency Check
            used_by = []
            for p in design.userParameters:
                if p.name == param_name: continue
                # Exact name check in expression using regex boundary
                if re.search(rf"\b{re.escape(param_name)}\b", p.expression):
                    used_by.append(p.name)
            
            if used_by:
                args.returnData = json.dumps({
                    'status': 'error', 
                    'msg': f"Used by: {', '.join(used_by[:3])}" + ("..." if len(used_by)>3 else "")
                })
                return
            
            param.deleteMe()
            adsk.doEvents() 
            
            if design.userParameters.itemByName(param_name):
                raise Exception("Fusion refused delete (possible hidden dependency)")
                
            args.returnData = json.dumps({'status': 'success', 'msg': f"Deleted {param_name}"})
            
        except Exception as e:
            msg = str(e)
            if "dependency" in msg.lower() or "refer" in msg.lower():
                final_msg = f"Cannot delete '{param_name}': Used in design."
            else:
                final_msg = f"Delete failed: {msg}"
            args.returnData = json.dumps({'status': 'error', 'msg': final_msg})

    def _handle_batch_update(self, data, args):
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            args.returnData = json.dumps({'status': 'error', 'msg': 'No design'})
            return

        items = data.get('items', []) if isinstance(data, dict) else data
        suppress = data.get('suppress_refresh', False) if isinstance(data, dict) else False
        
        count = 0
        errors = []
        
        for item in items:
            name = item.get('name')
            expr = item.get('expression')
            cmt = item.get('comment')
            if not name or not expr: continue
            
            try:
                existing = design.userParameters.itemByName(name)
                if existing:
                    if existing.expression != expr: existing.expression = expr
                    if cmt and existing.comment != cmt: existing.comment = cmt
                    count += 1
                else:
                    val_input = adsk.core.ValueInput.createByString(expr)
                    try:
                        design.userParameters.add(name, val_input, "mm", cmt or "")
                        count += 1
                    except: # Try unitless
                        design.userParameters.add(name, val_input, "", cmt or "")
                        count += 1
            except Exception as e:
                errors.append(f"{name}: {str(e)}")

        adsk.doEvents() # Flush

        if errors:
            msg = f"Refreshed. {len(errors)} errors ({errors[0]})"
            args.returnData = json.dumps({'status': 'warning', 'msg': msg})
        else:
            msg = f"Updated {count} parameters"
            args.returnData = json.dumps({'status': 'success', 'msg': msg})
        
        if not suppress:
            self._send_all_params()

    # --- BACKGROUND HANDLERS ---
    
    def on_command_terminated(self, args):
        """
        Called when any Fusion command finishes.
        Used for:
        1. Auto-Sorting new parameters (Hands-Free)
        2. Detecting Rename events (Future: Body Rename Sync)
        """
        try:
            cmd_def = args.command.parentCommandDefinition
            cmd_id = cmd_def.id
            cmd_name = cmd_def.name
            
            # log_diag(f"CMD FINISHED: {cmd_name} ({cmd_id})")
            
            # TRIGGER 1: GEOMETRY CREATION -> AUTO-SORT
            # If user did Extrude, Revolve, Fillet, they likely bound a param to a body.
            # Run Crawler to update tags.
            creation_cmds = ['Extrude', 'Revolve', 'Hole', 'Fillet', 'Chamfer', 'Sweep', 'Loft', 'Combine']
            
            should_sort = False
            for c in creation_cmds:
                if c in cmd_name or c in cmd_id:
                    should_sort = True
                    break
            
            if should_sort:
                # log_diag("Triggering Auto-Sort...")
                self._auto_sort_params()
                self._send_all_params()
                
            # TRIGGER 2: RENAME -> SYNC (Future Implementation)
            # If 'Rename' happened, we should re-crawl or check token map.
            # For now, simplistic re-crawl is fine.
            if 'Rename' in cmd_name:
                 # log_diag("Triggering Rename Sync...")
                 self._auto_sort_params() # This handles renaming too!
                 self._send_all_params()
                 
        except:
            pass

    # --- HELPERS ---

    def _auto_sort_params(self, data=None, args=None):
        """
        Uses ZenDependencyCrawler to find bodies associated with parameters
        and updates their group tags if they are uncategorized.
        """
        log_diag("--> Executing Auto-Sort...")
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design: 
                log_diag("No active design")
                return

            crawler = ZenDependencyCrawler(design)
            count = 0
            
            # log_diag(f"Scanning {design.userParameters.count} parameters...")
            
            for param in design.userParameters:
                if param.name == '_zen_current_preset': continue
                
                # Check if already grouped
                comment = param.comment
                if comment.startswith('['): continue # Already grouped
                
                # Crawl
                body_name = crawler.get_param_body_name(param)
                if body_name:
                    # Update Comment: "[BodyName] Original Comment"
                    new_comment = f"[{body_name}] {comment}"
                    param.comment = new_comment
                    count += 1
                    log_diag(f"  Sorted {param.name} -> {body_name}")
            
            log_diag(f"Auto-Sort Complete. Updated: {count}")

            if count > 0:
                self._send_notification(f"Auto-sorted {count} params", "success")
            else:
                self._send_notification("No new associations found.", "info")
                
        except Exception as e:
            log_diag(f"Auto-Sort Error: {str(e)}")
            self._send_notification(f"Sort Error: {str(e)}", "error")
            
        # ALWAYS Refresh Table so UI doesn't hang
        self._send_all_params()

    def _send_initial_data(self):
        payload = self._gather_payload_dict()
        self._send_response(payload, 'init_all')

    def _send_all_params(self):
        pl = self._get_param_list()
        self._send_response(pl, 'update_table')

    def _send_notification(self, message, status):
        data = json.dumps({'message': message, 'status': status, 'type': 'notification', 'timestamp': time.time()})
        self._send_to_html('response', data)

    def _send_response(self, content, type_str):
        data = json.dumps({'content': content, 'type': type_str, 'timestamp': time.time()})
        self._send_to_html('response', data)

    def _send_to_html(self, action, data):
        app = adsk.core.Application.get()
        ui = app.userInterface
        palette = ui.palettes.itemById(self.palette_id)
        if palette:
            try: palette.sendInfoToHTML(action, data)
            except: pass

    def _send_error(self, msg):
        self._send_notification(msg, "error")

    def _get_param_list(self):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design: return []
            
            param_list = []
            
            # Helper to parse "[Group] Comment"
            def parse_group(comment):
                group = "Uncategorized"
                clean_comment = comment
                if comment and comment.startswith('['):
                    end_idx = comment.find(']')
                    if end_idx != -1:
                        group = comment[1:end_idx].strip()
                        clean_comment = comment[end_idx+1:].strip()
                return group, clean_comment

            # User Params
            for param in design.userParameters:
                if param.name == '_zen_current_preset': continue
                group, clean_cmt = parse_group(param.comment)
                param_list.append({
                    'name': param.name, 'expression': param.expression,
                    'unit': param.unit, 'comment': clean_cmt, 
                    'group': group, 'fullComment': param.comment,
                    'isUser': True
                })
            
            # Model Params (Limit 50)
            count = 0
            for param in design.allParameters:
                if count > 50: break
                if design.userParameters.itemByName(param.name): continue
                # Model params don't usually have comments we control, but just in case
                group, clean_cmt = parse_group(param.comment)
                param_list.append({
                    'name': param.name, 'expression': param.expression,
                    'unit': param.unit, 'comment': clean_cmt, 
                    'group': "Model Parameters", 'fullComment': param.comment,
                    'isUser': False
                })
                count += 1
            return param_list
        except: return []

    def _gather_payload_dict(self):
        presets = self.preset_manager.load_all()
        params = self._get_param_list()
        fits = self.fit_manager.load_fits() # Load fits!
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
            'presets': presets,
            'params': params,
            'fits': fits,
            'current_preset': current_preset,
            'legacy_params': has_legacy
        }
