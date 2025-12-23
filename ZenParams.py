import adsk.core, adsk.fusion, traceback
import os, sys, importlib

# Ensure local lib directory is in path
APP_PATH = os.path.dirname(os.path.abspath(__file__))
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)

# Reload Dependencies
import config
import lib.zen_utils
import lib.zen_crawler
import lib.zen_handler
importlib.reload(config)
importlib.reload(lib.zen_utils)
importlib.reload(lib.zen_crawler)
importlib.reload(lib.zen_handler)

from lib.zen_handler import ZenPaletteEventHandler

# Global instance for Fusion to hold onto
_addin = None

class ZenParamsAddin:
    def __init__(self):
        self.app = adsk.core.Application.get()
        self.ui = self.app.userInterface
        self.handlers = []
        self.palette = None
        
    def run(self):
        """Startup Entry Point"""
        try:
            adsk.autoTerminate(False)
            
            # 1. Cleanup Old (Safety)
            self._cleanup_ui()
            
            # 2. Create Command Definition
            cmd_def = self.ui.commandDefinitions.addButtonDefinition(
                config.CMD_ID, 
                'ZenParams Pro', 
                'Open ZenParams Palette', 
                os.path.join(APP_PATH, 'resources')
            )
            
            # 3. Add to Toolbar
            modify_panel = self.ui.allToolbarPanels.itemById(config.PANEL_ID)
            if modify_panel:
                modify_panel.controls.addCommand(cmd_def)
                
            # 4. Bind Command Created Event
            on_created = CommandCreatedHandler(self)
            cmd_def.commandCreated.add(on_created)
            self.handlers.append((cmd_def.commandCreated, on_created))
            
            # 5. Show Palette immediately
            self.show_palette()
            
            # 6. Global Application Events
            self._register_global_events()
            
            lib.zen_utils.log_diag("ZenParams v2 STARTED.")

        except:
            self.ui.messageBox('Startup Failed:\n{}'.format(traceback.format_exc()))

    def stop(self):
        """Shutdown Entry Point"""
        try:
            # 1. Clean UI
            self._cleanup_ui()
            
            # 2. Unregister ALL Handlers
            for event, handler in self.handlers:
                try: event.remove(handler)
                except: pass
            self.handlers.clear()
            

                
            lib.zen_utils.log_diag("ZenParams v2 STOPPED.")
            
        except:
            if self.ui:
                self.ui.messageBox('Shutdown Failed:\n{}'.format(traceback.format_exc()))

    def show_palette(self, toggle=False):
        """Show or Toggle Palette"""
        self.palette = self.ui.palettes.itemById(config.PALETTE_ID)
        
        if not self.palette:
            html_path = os.path.join(APP_PATH, 'ui', 'index.html')
            # Normalize path for binding
            html_file_url = html_path.replace('\\', '/')
            if not html_file_url.startswith('file:///'):
                 if not html_file_url.startswith('/'): html_file_url = '/' + html_file_url
                 html_file_url = 'file://' + html_file_url
            
            self.palette = self.ui.palettes.add(
                config.PALETTE_ID, 'ZenParams Pro', html_file_url, True, True, True, 320, 600
            )
            try:
                self.palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
            except:
                lib.zen_utils.log_diag("WARN: Failed to set Docking State (pArea)")
            
            # Bind HTML Event
            on_html_event = ZenPaletteEventHandler(config.PALETTE_ID, APP_PATH)
            self.palette.incomingFromHTML.add(on_html_event)
            self.handlers.append((self.palette.incomingFromHTML, on_html_event))
            
        else:
            if toggle:
                self.palette.isVisible = not self.palette.isVisible
            else:
                self.palette.isVisible = True
    
    def _cleanup_ui(self):
        """Remove Command and Palette interfaces"""
        cmd = self.ui.commandDefinitions.itemById(config.CMD_ID)
        if cmd: cmd.deleteMe()
        
        panel = self.ui.allToolbarPanels.itemById(config.PANEL_ID)
        if panel:
            ctrl = panel.controls.itemById(config.CMD_ID)
            if ctrl: ctrl.deleteMe()
            
        pal = self.ui.palettes.itemById(config.PALETTE_ID)
        if pal: pal.deleteMe()

    def _register_global_events(self):
        """Register App-level events"""
        # Startup
        if not self.app.isStartupComplete:
            on_start = StartupCompletedHandler(self)
            self.app.startupCompleted.add(on_start)
            self.handlers.append((self.app.startupCompleted, on_start))
            
        # Doc Activation
        on_doc = DocumentActivatedHandler(self)
        self.app.documentActivated.add(on_doc)
        self.handlers.append((self.app.documentActivated, on_doc))

# -----------------------------------------------------------------------------
# EVENT HANDLERS
# -----------------------------------------------------------------------------

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, addin):
        super().__init__()
        self.addin = addin
    def notify(self, args):
        try:
            self.addin.show_palette(toggle=True)
        except:
            if self.addin.ui: self.addin.ui.messageBox(traceback.format_exc())

class StartupCompletedHandler(adsk.core.ApplicationEventHandler):
    def __init__(self, addin):
        super().__init__()
        self.addin = addin
    def notify(self, args):
        try:
            self.addin.show_palette(toggle=False)
        except:
            lib.zen_utils.log_diag(traceback.format_exc())

class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
    def __init__(self, addin):
        super().__init__()
        self.addin = addin
    def notify(self, args):
        # Refresh logic here if needed
        pass

# -----------------------------------------------------------------------------
# LIFECYCLE
# -----------------------------------------------------------------------------

def run(context):
    global _addin
    try:
        _addin = ZenParamsAddin()
        _addin.run()
    except:
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())

def stop(context):
    global _addin
    if _addin:
        _addin.stop()
        _addin = None
