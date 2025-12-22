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
        self.crawler = None # Persistent Crawler Instance

    # --- BACKGROUND HANDLERS ---
    
    def on_command_terminated(self, args):
        """
        Called when any Fusion command finishes.
        Handles Auto-Sort triggers efficiently.
        """
        try:
            cmd_def = args.command.parentCommandDefinition
            cmd_id = cmd_def.id
            cmd_name = cmd_def.name
            
            # log_diag(f"CMD FINISHED: {cmd_name} ({cmd_id})")
            
            # TRG 1: GEOMETRY CREATION -> REFRESH MAP + SORT
            # If new bodies/features created, we must rebuild the map.
            geometry_cmds = ['Extrude', 'Revolve', 'Hole', 'Fillet', 'Chamfer', 'Sweep', 'Loft', 'Combine', 'Thicken', 'Pattern', 'Mirror']
            
            # TRG 2: DIMENSION/USAGE -> SORT ONLY (FAST)
            # If sketch dimension added, map is valid, just re-scan usage.
            usage_cmds = ['Dimension', 'Sketch', 'Edit', 'Parameters']
            
            is_geo = any(x in cmd_name or x in cmd_id for x in geometry_cmds)
            is_usage = any(x in cmd_name or x in cmd_id for x in usage_cmds)
            
            if is_geo or is_usage:
                # log_diag(f"Triggering Auto-Sort (Geo={is_geo})")
                self._auto_sort_params(force_map_refresh=is_geo)
                self._send_all_params()

        except:
            pass

    # --- HELPERS ---

    def _get_crawler(self, design):
        # Lazy Load / Persist
        if self.crawler is None or self.crawler.design != design:
             self.crawler = ZenDependencyCrawler(design)
        return self.crawler

    def _auto_sort_params(self, data=None, args=None, force_map_refresh=False):
        """
        Uses ZenDependencyCrawler to find bodies associated with parameters.
        args: force_map_refresh (bool) - specific optimization for background handler.
        """
        # log_diag("--> Executing Auto-Sort...")
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design: return
            
            crawler = self._get_crawler(design)
            
            if force_map_refresh:
                crawler.refresh_map()
                
            count = 0
            
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
            
            if count > 0:
                log_diag(f"Auto-Sort: {count} updated.")
                adsk.doEvents()
                self._send_notification(f"Auto-sorted {count} params", "success")
            elif data: # Only notify "No changes" if manually triggered (data is not None)
                self._send_notification("No new associations found.", "info")
                
        except Exception as e:
            log_diag(f"Auto-Sort Error: {str(e)}")
            if data: self._send_notification(f"Sort Error: {str(e)}", "error")
            
        # ALWAYS Refresh Table
        self._send_all_params()

    def notify(self, args):
        try:
            if not args.data: return
            html_args = json.loads(args.data)
            action = html_args.get('action')
            data = html_args.get('data')
            
            if not action: return

            if action == 'get_initial_data':
                self._handle_get_initial_data(data, args)
            elif action == 'save_preset':
                self._handle_save_preset(data, args)
            elif action == 'apply_preset':
                self._handle_apply_preset(data, args) # Legacy support if needed
            elif action == 'delete_preset':
                self._handle_delete_preset(data, args)
            elif action == 'set_current_preset':
                self._handle_set_current_preset(data, args)
            elif action == 'delete_param':
                self._handle_delete_param(data, args)
            elif action == 'batch_update':
                self._handle_batch_update(data, args)
            elif action == 'refresh':
                self._handle_refresh(data, args)
            elif action == 'close_palette':
                self._handle_close_palette(data, args)
            elif action == 'auto_sort':
                self._auto_sort_params(data, args)
            elif action == 'save_fit_defaults':
                self._handle_save_fit_defaults(data, args)
            elif action == 'get_active_doc_info':
                self._handle_get_doc_info(data, args)
                
        except Exception as e:
            self._send_error(f"Event Handler Error: {e}")
            log_diag(traceback.format_exc())

    # --- HANDLERS ---

    def _handle_get_initial_data(self, data, args):
        try:
            payload = self._gather_payload_dict()
            args.returnData = json.dumps({'content': payload, 'type': 'init_all'})
        except Exception as e:
            log_diag(f"Init Data Error: {e}")
            args.returnData = json.dumps({'content': {}, 'type': 'error', 'msg': str(e)})

    def _handle_save_preset(self, data, args):
        name = data.get('name')
        params = data.get('params')
        if self.preset_manager.save_preset(name, params):
            self._send_notification(f"Saved '{name}'", "success")
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
        if not preset_name:
             # Clear preset
             self._set_preset_param(None)
        else:
             self._set_preset_param(preset_name)
        self._send_initial_data()

    def _set_preset_param(self, name):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design: return
            p_name = '_zen_current_preset'
            exist = design.userParameters.itemByName(p_name)
            if name:
                if exist: exist.comment = name
                else: design.userParameters.add(p_name, adsk.core.ValueInput.createByString('1'), '', name)
            else:
                if exist: exist.deleteMe()
            adsk.doEvents()
        except: pass

    def _handle_batch_update(self, data, args):
        items = data.get('items', [])
        suppress = data.get('suppress_refresh', False)
        
        count = 0
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design: return
            
            for item in items:
                try:
                    name = item.get('name')
                    expr = item.get('expression')
                    comment = item.get('comment')
                    is_user = item.get('isUser', True)
                    
                    if not name: continue
                    
                    # Try to find param
                    param = design.userParameters.itemByName(name)
                    if not param:
                        # Maybe it is a model param?
                        param = design.allParameters.itemByName(name)
                        
                    if param:
                        if expr and param.expression != expr:
                            param.expression = expr
                            count += 1
                        
                        if comment is not None and param.comment != comment:
                            param.comment = comment
                            count += 1
                    else:
                        # New Parameter creation (if intended)
                        # For batch update, we usually only update existing.
                        # New params are created via separate logic or explicit create.
                        # But if Logic.js sends new row as batch_update?
                        # Logic.js sends 'new_param' as name for new rows, then user types name.
                        # If user types name 'Width' and hits enter, it sends batch_update with name='Width'.
                        # If 'Width' doesn't exist, we should create it?
                        # ZenParams v11 seems to implies seamless creation.
                        if is_user and expr:
                             # Create new
                             design.userParameters.add(name, adsk.core.ValueInput.createByString(expr), "mm", comment or "")
                             count += 1
                except:
                    continue
            
            if count > 0:
                adsk.doEvents()
                
        except Exception as e:
            log_diag(f"Batch Update Error: {e}")
        
        if not suppress:
            self._send_all_params()

    def _handle_delete_param(self, data, args):
        name = data.get('name')
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            p = design.userParameters.itemByName(name)
            if p: 
                p.deleteMe()
                args.returnData = json.dumps({'status': 'success', 'msg': 'Deleted'})
            else:
                args.returnData = json.dumps({'status': 'error', 'msg': 'Not found'})
        except Exception as e:
            args.returnData = json.dumps({'status': 'error', 'msg': str(e)})

    def _handle_close_palette(self, data, args):
        app = adsk.core.Application.get()
        ui = app.userInterface
        p = ui.palettes.itemById(self.palette_id)
        if p: p.isVisible = False

    def _handle_refresh(self, data, args):
        self._send_all_params()

    def _handle_save_fit_defaults(self, data, args):
        fits = data.get('fits')
        if self.fit_manager.save_fits(fits):
            self._send_notification("Fits saved", "success")
            self._send_initial_data()

    def _handle_get_doc_info(self, data, args):
        doc_name = ""
        doc_id = ""
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design and design.parentDocument:
                doc_name = design.parentDocument.name
                doc_id = design.parentDocument.creationId
        except: pass
        args.returnData = json.dumps({'name': doc_name, 'id': doc_id})


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
                try:
                    if param.name == '_zen_current_preset': continue
                    # Safely access properties
                    name = param.name
                    expr = param.expression
                    unit = param.unit
                    full_cmt = param.comment
                    
                    group, clean_cmt = parse_group(full_cmt)
                    
                    param_list.append({
                        'name': name, 'expression': expr,
                        'unit': unit, 'comment': clean_cmt, 
                        'group': group, 'fullComment': full_cmt,
                        'isUser': True
                    })
                except: continue # Skip bad apple
            
            # Model Params (Limit 50)
            count = 0
            for param in design.allParameters:
                if count > 50: break
                try:
                    if design.userParameters.itemByName(param.name): continue
                    
                    name = param.name
                    expr = param.expression
                    unit = param.unit
                    full_cmt = param.comment
                    
                    group, clean_cmt = parse_group(full_cmt)
                    
                    param_list.append({
                        'name': name, 'expression': expr,
                        'unit': unit, 'comment': clean_cmt, 
                        'group': "Model Parameters", 'fullComment': full_cmt,
                        'isUser': False
                    })
                    count += 1
                except: continue

            # log_diag(f"Generated Param List: {len(param_list)} items")
            return param_list
        except Exception as e:
            log_diag(f"get_param_list Crash: {e}")
            return []

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
