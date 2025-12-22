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
