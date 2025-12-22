import adsk.core
import adsk.fusion
import traceback
import os
import sys

import importlib

# Ensure local lib directory is in path
APP_PATH = os.path.dirname(os.path.abspath(__file__))
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)

# Force Reload to fix Fusion 360 caching issues
import lib.zen_utils
import lib.zen_crawler
import lib.zen_handler
importlib.reload(lib.zen_utils)
importlib.reload(lib.zen_crawler)
importlib.reload(lib.zen_handler)

from lib.zen_handler import ZenPaletteEventHandler

# Global Reference
_handlers = []
_app = None
_ui = None
_last_active_doc_name = None 
_palette_handler = None

CMD_ID = 'zenparams_cmd_v2'
PALETTE_ID = 'zenparams_palette_v8'

# -----------------------------------------------------------------------------
# EVENT HANDLERS (Top Level)
# -----------------------------------------------------------------------------

class StartupCompletedHandler(adsk.core.ApplicationEventHandler):
    def notify(self, args):
        try: show_palette()
        except: pass

class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
    def notify(self, args):
        global _last_active_doc_name
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            current_doc_id = ""
            if design and design.parentDocument:
                try: current_doc_id = design.parentDocument.creationId
                except: current_doc_id = design.parentDocument.name

            if _last_active_doc_name == current_doc_id: return
            _last_active_doc_name = current_doc_id
             
            # Send refresh signal via a temporary handler wrapper or direct event
            # Note: Ideally we keep a reference to the active handler, but given 
            # Fusion's stateless callback nature, we instantiate a sender helper.
            # Simpler: Just make the palette refresh itself if visible.
            palette = _ui.palettes.itemById(PALETTE_ID)
            if palette and palette.isVisible:
                 # Re-inject handler to force update? 
                 # Actually, we just need to trigger the initial data push.
                 # We can piggyback off the existing handler attached to the palette
                 pass 

        except: pass

class CommandStartingHandler(adsk.core.ApplicationCommandEventHandler):
    def notify(self, args):
        try:
             cmd_name = args.command.parentCommandDefinition.name
             lib.zen_utils.log_diag(f"START-EVT: {cmd_name}")
        except: pass

class CommandTerminatedHandler(adsk.core.ApplicationCommandEventHandler):
    def notify(self, args):
        global _palette_handler
        try:
            lib.zen_utils.log_file("MainEvt: Fired") 
        except: pass

        try:
             if _palette_handler:
                 _palette_handler.on_command_terminated(args)
        except: pass

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try: show_palette(toggle=True)
        except: pass

# -----------------------------------------------------------------------------
# MAIN HELPERS
# -----------------------------------------------------------------------------

def show_palette(toggle=False):
    global _ui, _handlers, _palette_handler
    
    palette = _ui.palettes.itemById(PALETTE_ID)
    if not palette:
        html_path = os.path.join(APP_PATH, 'ui', 'index.html')
        html_file_url = html_path.replace('\\', '/')
        if not html_file_url.startswith('file:///'):
             if not html_file_url.startswith('/'): html_file_url = '/' + html_file_url
             html_file_url = 'file://' + html_file_url
        
        palette = _ui.palettes.add(PALETTE_ID, 'ZenParams Pro', html_file_url, True, True, True, 320, 600)
        
        try: palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
        except: pass

        # Register Event Handler from Lib (ONLY ON CREATION)
        on_html_event = ZenPaletteEventHandler(PALETTE_ID, APP_PATH)
        palette.incomingFromHTML.add(on_html_event)
        _handlers.append(on_html_event) # Keep alive
        _palette_handler = on_html_event # Store for background events
    else:
        if toggle: palette.isVisible = not palette.isVisible
        else: palette.isVisible = True

def run(context):
    global _app, _ui, _palette_handler
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        adsk.autoTerminate(False)
        
        # Add Command
        cmd_def = _ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def: cmd_def.deleteMe()
        cmd_def = _ui.commandDefinitions.addButtonDefinition(CMD_ID, 'ZenParams Pro', 'Open ZenParams Palette', './resources')
        
        on_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)
        
        # Add to Toolbar
        modify_panel = _ui.allToolbarPanels.itemById('SolidModifyPanel')
        if modify_panel:
            if not modify_panel.controls.itemById(CMD_ID):
                modify_panel.controls.addCommand(cmd_def)
            
        # Clean old palette
        palette = _ui.palettes.itemById(PALETTE_ID)
        if palette: palette.deleteMe()
        
        show_palette()
        
        lib.zen_utils.log_diag("ZenParams v11 STARTUP: Handlers Registered")
        
        # DEBUG: Verify Log Path
        log_path_debug = os.path.join(lib.zen_utils.APP_PATH, 'zen_debug.log')
        lib.zen_utils.log_diag(f"Log Path: {log_path_debug}")
        
        try:
            lib.zen_utils.log_file(f"ZenParams Startup. Handlers: {len(_handlers)}")
            lib.zen_utils.log_diag("Log File Write: SUCCESS")
        except Exception as e:
            lib.zen_utils.log_diag(f"Log File Write: FAILED ({e})")
        
        # Startup Handler
        if not _app.isStartupComplete:
            on_start = StartupCompletedHandler()
            _app.startupCompleted.add(on_start)
            _handlers.append(on_start)
            
        # Doc Handler
        on_doc = DocumentActivatedHandler()
        _app.documentActivated.add(on_doc)
        _handlers.append(on_doc)
        
        
        # Command Terminated Handler (Background Watcher)
        on_term = CommandTerminatedHandler()
        is_ok_term = _ui.commandTerminated.add(on_term)
        _handlers.append(on_term)
        
        # Command Starting Handler (Comparison Test)
        on_start_cmd = CommandStartingHandler()
        is_ok_start = _ui.commandStarting.add(on_start_cmd)
        _handlers.append(on_start_cmd)
        
        lib.zen_utils.log_diag(f"handlers: {len(_handlers)} | Term={is_ok_term} Start={is_ok_start}")
        lib.zen_utils.log_diag("ZenParams v11 READY")
        
    except:
        if _ui: _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    global _ui
    try:
        palette = _ui.palettes.itemById(PALETTE_ID)
        if palette: palette.deleteMe()
        
        cmd = _ui.commandDefinitions.itemById(CMD_ID)
        if cmd: cmd.deleteMe()
        
        modify_panel = _ui.allToolbarPanels.itemById('SolidModifyPanel')
        if modify_panel:
            c = modify_panel.controls.itemById(CMD_ID)
            if c: c.deleteMe()
    except: pass
