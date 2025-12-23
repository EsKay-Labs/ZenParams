import adsk.core
import adsk.fusion
import json
import traceback
import time
import re
from .zen_utils import log_diag, log_file, PresetManager, FitManager
from .zen_crawler import ZenDependencyCrawler
from .zen_storage import ZenStorage

class ZenPaletteEventHandler(adsk.core.HTMLEventHandler):
    """Handles messages coming from the HTML Palette."""
    
    def __init__(self, palette_id: str, root_path: str):
        super().__init__()
        self.palette_id = palette_id
        self.preset_manager = PresetManager(root_path)
        self.fit_manager = FitManager(root_path)
        self.crawler = None # Persistent Crawler Instance
        self._data_version = 0 # Incremented when data changes (for JS polling)

    # --- BACKGROUND HANDLERS ---
    
    def on_command_terminated(self, args):
        """
        Called when any Fusion command finishes.
        Handles Auto-Sort triggers efficiently.
        """
        # Safe command extraction
        cmd_id = "Unknown"
        cmd_name = "Unknown"
        try:
            # NOTE: For commandTerminated, use args.commandDefinition DIRECTLY
            # (NOT args.command.parentCommandDefinition, that's for CommandCreatedEventHandler)
            if args and args.commandDefinition:
                cmd_def = args.commandDefinition
                cmd_id = cmd_def.id or "NoID"
                cmd_name = cmd_def.name or "NoName"
        except Exception as e:
            log_diag(f"CMD Extract Error: {e}")
            return # Can't proceed without command info
        
        # Avoid infinite loop: Text Command writes trigger this event!
        if 'TextCommandInput' in cmd_id: return

        # Debug: See what commands are firing (SAFE)
        log_file(f"Cmd Terminated: {cmd_name} [{cmd_id}]")
        log_diag(f"CMD: {cmd_name} [{cmd_id}]") # Visual Confirmation
        
        try:
            # TRG 1: GEOMETRY CREATION -> MAP REFRESH & SORT
            # If new bodies/features created, we must rebuild the map.
            geometry_cmds = ['Extrude', 'Revolve', 'Hole', 'Fillet', 'Chamfer', 'Sweep', 'Loft', 'Combine', 'Thicken', 'Pattern', 'Mirror']
            
            # TRG 2: DIMENSION/USAGE -> SORT ONLY (FAST)
            # If sketch dimension added, map is valid, just re-scan usage.
            usage_cmds = ['Dimension', 'Sketch', 'Edit', 'Parameters', 'Commit', 'Finish', 'Update', 'Compute']
            
            is_geo = any(x in cmd_name or x in cmd_id for x in geometry_cmds)
            is_usage = any(x in cmd_name or x in cmd_id for x in usage_cmds)
            
            if is_geo or is_usage:
                log_file(f"Trigger: {cmd_name} (Refreshing Map)")
                # ALWAYS refresh map to ensure new sketches/features are found
                self._auto_sort_params(force_map_refresh=True)
                self._send_all_params()

        except Exception as e:
            log_diag(f"Trigger Error: {e}")

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
                
                # Get current comment
                comment = param.comment
                
                # Detect and clean various corrupted/outdated bracket formats:
                # 1. List format: "[['body']]" or "['body', 'other']"
                # 2. Old Shared format: "[Shared (2)]" "[Shared (4)]" etc.
                needs_clean = False
                
                if comment.startswith("[['"): needs_clean = True
                elif comment.startswith("['"): needs_clean = True
                elif comment.startswith("[Shared ("): needs_clean = True  # Old shared format
                
                if needs_clean:
                    try:
                        end_bracket = comment.find(']')
                        if end_bracket != -1 and end_bracket < len(comment) - 1:
                            comment = comment[end_bracket + 1:].strip()
                        else:
                            comment = ""
                        param.comment = comment
                        log_diag(f"  Cleaned old bracket: {param.name}")
                    except:
                        comment = ""
                
                # Skip if already properly grouped with CURRENT format
                # (clean single bracket like "[BodyName]" or "[Shared]" or "[Unused]")
                if comment.startswith('[') and ']' in comment:
                    continue
                
                # Crawl - crawler returns None or list of body names
                body_list = crawler.get_param_body_name(param)
                
                # Determine category from body list
                extra_info = ""  # Additional info to add to comment
                
                if body_list is None or len(body_list) == 0:
                    # Unused - no references found
                    category = "Unused"
                elif len(body_list) == 1:
                    # Body-specific: used by exactly one body
                    category = body_list[0]
                    # Clean up root component name
                    if category == '(Unsaved)': 
                        category = 'Main Design'
                else:
                    # Shared: used by multiple bodies - single folder
                    category = "Shared"
                    # Add body names to comment so user knows which bodies
                    body_names = ', '.join(body_list[:6])  # Limit to 6 names
                    if len(body_list) > 6:
                        body_names += f', +{len(body_list) - 6} more'
                    extra_info = f" (Used by: {body_names})"
                
                if category:
                    # Update Comment: "[Category] Original Comment (Used by: ...)"
                    new_comment = f"[{category}] {comment}{extra_info}"
                    param.comment = new_comment
                    count += 1
                    adsk.doEvents() # Prevent race condition
                    log_diag(f"  Sorted {param.name} -> {category}")
                # else:
                #     log_diag(f"  Unsorted: {param.name} (No usage found)")
            
            if count > 0:
                log_diag(f"Auto-Sort: {count} updated.")
                self._data_version += 1 # Signal JS to refresh
                adsk.doEvents()
                time.sleep(0.25) # Wait for Fusion to commit changes
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
            elif action == 'get_data_version':
                args.returnData = json.dumps({'version': self._data_version})
                
        except Exception as e:
            self._send_error(f"Event Handler Error: {e}")
            log_diag(traceback.format_exc())

    # --- HANDLERS ---

    def _handle_get_initial_data(self, data, args):
        try:
            # Auto-Sort on Startup (User Request)
            log_diag("Startup: Running Auto-Sort...")
            self._auto_sort_params(force_map_refresh=True)
            
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
        
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design:
                storage = ZenStorage(design)
                if not preset_name:
                    storage.delete('current_preset')
                else:
                    storage.set('current_preset', preset_name)
                adsk.doEvents()
        except: 
            log_diag(traceback.format_exc())
            
        self._send_initial_data()

    def _handle_batch_update(self, data, args):
        items = []
        suppress = False
        
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('items', [])
            suppress = data.get('suppress_refresh', False)
            
        count = 0
        new_param_created = False  # Track if we created any new parameters
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
                             new_param_created = True  # Flag that we created a new parameter
                except:
                    continue
            
            if count > 0:
                adsk.doEvents()
                
        except Exception as e:
            log_diag(f"Batch Update Error: {e}")
        
        if not suppress:
            # If we created new parameters, auto-sort to put them in correct folders
            if new_param_created:
                log_diag("Auto-sorting after new parameter creation...")
                self._auto_sort_params(force_map_refresh=False)  # Sort will also send params
            else:
                self._send_all_params()

    def _handle_delete_param(self, data, args):
        """
        Safe parameter deletion with pre-validation.
        Checks dependencies BEFORE attempting delete.
        """
        name = data.get('name')
        log_diag(f"Delete Request: {name}")
        
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design:
                args.returnData = json.dumps({'status': 'error', 'msg': 'No active design'})
                return
                
            # Find parameter
            param = design.userParameters.itemByName(name)
            if not param:
                args.returnData = json.dumps({'status': 'error', 'msg': f"'{name}' not found"})
                return
            
            # PRE-CHECK: Gather dependencies before attempting delete
            # API: dependentParameters returns parameters that reference this one
            deps = param.dependentParameters
            dep_names = []
            if deps:
                for i in range(deps.count):
                    try:
                        dep = deps.item(i)
                        dep_name = dep.name if hasattr(dep, 'name') else type(dep).__name__
                        dep_names.append(dep_name)
                    except: pass
            
            if dep_names:
                msg = f"Used by: {', '.join(dep_names[:5])}"
                if len(dep_names) > 5:
                    msg += f" (+{len(dep_names) - 5} more)"
                log_diag(f"Delete Blocked: {name} -> {msg}")
                args.returnData = json.dumps({'status': 'error', 'msg': f"Cannot delete: {msg}"})
                return
            
            # SAFE TO DELETE
            try:
                param.deleteMe()
                self._data_version += 1  # Trigger UI sync
                adsk.doEvents()
                log_diag(f"Deleted: {name}")
                args.returnData = json.dumps({'status': 'success', 'msg': f"Deleted '{name}'"})
            except Exception as e:
                log_diag(f"Delete Failed (Fusion): {e}")
                args.returnData = json.dumps({'status': 'error', 'msg': f"Fusion error: {str(e)}"})
                
        except Exception as e:
            log_diag(f"Delete Critical Error: {e}")
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
        adsk.doEvents() # Flush pending updates before read
        pl = self._get_param_list()
        log_diag(f"Sending {len(pl)} params to UI...")
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
                    
                    # Strip unit from expression for display
                    display_val = expr
                    if unit and expr.endswith(unit):
                        display_val = expr[:-len(unit)].strip()
                    
                    group, clean_cmt = parse_group(full_cmt)
                    
                    param_list.append({
                        'name': name, 'expression': display_val,
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
                    
                    # Strip unit from expression for display
                    display_val = expr
                    if unit and expr.endswith(unit):
                        display_val = expr[:-len(unit)].strip()
                    
                    group, clean_cmt = parse_group(full_cmt)
                    
                    param_list.append({
                        'name': name, 'expression': display_val,
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
                current_preset = ZenStorage.get_current_preset_name(design)
                
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
