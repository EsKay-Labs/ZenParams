import adsk.core, adsk.fusion, traceback
import unittest
import os
import sys
import shutil
import tempfile
import json
import math

# --- SETUP PATHS ---
APP_PATH = os.path.dirname(os.path.abspath(__file__))
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)

# Import ZenParams Tests
try:
    import lib.zen_utils as zen_utils
    from lib.zen_crawler import ZenDependencyCrawler
    from lib.zen_handler import ZenPaletteEventHandler
except ImportError:
    # If running from IDE context without full path
    pass

# --- CONSTANTS ---
TEST_DIR = os.path.join(APP_PATH, 'test_output')

# --- CONTEXT MANAGERS ---

class TestContext:
    """
    Creates a temporary Fusion Document for "Clean Room" testing.
    Ensures teardown even if tests fail.
    """
    def __init__(self):
        self.app = adsk.core.Application.get()
        self.doc = None
        self.design = None

    def __enter__(self):
        # Create new document
        self.doc = self.app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        
        # Ensure Direct Design for speed (no timeline usually needed test speed, 
        # BUT ZenCrawler relies on Timeline. So we MUST use Parametric.)
        self.design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close(False) # Close without saving


# --- TEST CLASSES ---

class TestPureLogic(unittest.TestCase):
    """
    Tests internal logic that doesn't strictly require Fusion geometry.
    Mocks file I/O for PresetManager and FitManager.
    """
    
    def setUp(self):
        # Create a temp directory for JSON files
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_preset_manager_io(self):
        """Verify Presets can be saved and loaded."""
        mgr = zen_utils.PresetManager(self.test_dir)
        
        # 1. Test Default Load
        defaults = mgr.get_defaults()
        self.assertIn("3DP Tolerances (Global)", defaults)
        
        # 2. Test Save
        test_data = {"param1": "10 mm", "param2": "5 mm"}
        mgr.save_preset("TestPreset", test_data)
        
        # 3. Test Reload
        loaded = mgr.load_all()
        self.assertIn("TestPreset", loaded)
        self.assertEqual(loaded["TestPreset"]["param1"], "10 mm")
        
        # 4. Test Delete
        mgr.delete_preset("TestPreset")
        reloaded = mgr.load_all()
        self.assertNotIn("TestPreset", reloaded)

    def test_fit_manager_migration(self):
        """Verify FitManager correctly migrates legacy flat files."""
        mgr = zen_utils.FitManager(self.test_dir)
        
        # 1. Seed legacy file
        legacy_data = {"bolt": 0.5, "my_custom_fit": 0.15}
        with open(os.path.join(self.test_dir, 'smart_fits.json'), 'w') as f:
            json.dump(legacy_data, f)
            
        # 2. Load (Trigger Migration)
        data = mgr.load_fits()
        
        # 3. Verify Structure
        # "bolt" should be an override of a standard fit
        bolt_fit = next(f for f in data['standards'] if f['id'] == 'bolt')
        self.assertAlmostEqual(bolt_fit['tol'], 0.5)
        
        # "my_custom_fit" should be in 'customs'
        custom_fit = next((f for f in data['customs'] if f['id'] == 'my_custom_fit'), None)
        self.assertIsNotNone(custom_fit)
        self.assertAlmostEqual(custom_fit['tol'], 0.15)


class TestFusionIntegration(unittest.TestCase):
    """
    Tests that interact with the Fusion 360 Design.
    """
    
    def test_dependency_crawler(self):
        """
        Verify ZenCrawler correctly identifies what body a parameter drives.
        Workflow: Create Box -> Create Param -> Map -> Check.
        """
        with TestContext() as ctx:
            design = ctx.design
            root = design.rootComponent
            
            # 1. Create a Box
            sk = root.sketches.add(root.xYConstructionPlane)
            lines = sk.sketchCurves.sketchLines
            rect = lines.addTwoPointRectangle(adsk.core.Point3D.create(0,0,0), adsk.core.Point3D.create(10,10,0))
            prof = sk.profiles.item(0)
            
            feats = root.features.extrudeFeatures
            ext_input = feats.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(5.0)) # 5cm
            ext = feats.add(ext_input)
            
            body = ext.bodies.item(0)
            body.name = "TestCube"
            
            # 2. Creates a User Parameter
            # Fusion API requires units in Loop or explicit ValueInput
            # We'll drive the Extrude Distance
            
            user_params = design.userParameters
            param = user_params.add("BoxHeight", adsk.core.ValueInput.createByReal(2.0), "mm", "Test Param")
            
            # 3. Link Param to Feature
            # To simulate "Usage", we assign the param name to the dimension
            # BUT: Extrude distance is a ModelParameter. We set its expression.
            # Find the extrude distance param
            
            # Usually: ext.extentOne.distance.expression = "BoxHeight"
            # But extentOne might be a DistanceExtentDefinition
            dist_def = adsk.fusion.DistanceExtentDefinition.cast(ext.extentOne)
            dist_param = dist_def.distance
            dist_param.expression = "BoxHeight"
            
            # 4. Crawl
            crawler = ZenDependencyCrawler(design)
            driven_bodies = crawler.get_param_body_name(param)
            
            # 5. Assert 
            # Should return ["TestCube"] (or "Root/TestCube" depending on implementation)
            self.assertIsNotNone(driven_bodies)
            # The crawler implementation returns "Comp/Body" 
            # In root, parentComponent is None? No, root is a component.
            # Let's check logic: comp_name = body.parentComponent.name
            
            expected_name = "TestCube" # Partial match check is safer
            found = any(expected_name in b for b in driven_bodies)
            self.assertTrue(found, f"Expected {expected_name} in {driven_bodies}")

    def test_auto_sort_logic(self):
        """
        Verify that _auto_sort_params in the handler updates comments.
        """
        # We need to instantiate the handler, but we don't need the UI.
        # We can mock the palette interaction or just call _auto_sort_params if it's decoupled enough.
        
        with TestContext() as ctx:
            design = ctx.design
            handler = ZenPaletteEventHandler("TEST_PALETTE", self.test_dir if hasattr(self, 'test_dir') else APP_PATH)
            
            # 1. Create Body & Param (similar to above)
            root = design.rootComponent
            sk = root.sketches.add(root.xYConstructionPlane)
            # Create Geometry
            lines = sk.sketchCurves.sketchLines
            lines.addTwoPointRectangle(adsk.core.Point3D.create(0,0,0), adsk.core.Point3D.create(5,5,0))
            prof = sk.profiles.item(0)
            ext = root.features.extrudeFeatures.addSimple(prof, adsk.core.ValueInput.createByReal(1.0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            body = ext.bodies.item(0)
            body.name = "SortingBody"
            
            # 2. Create Param linked to it
            param = design.userParameters.add("SideLen", adsk.core.ValueInput.createByString("50mm"), "mm", "Old Comment")
            
            # Link sketch dim to param
            # NOTE: addTwoPointRectangle does NOT add dims automatically in API. We must add one.
            line = lines.item(0)
            pt_text = adsk.core.Point3D.create(2.5, 6, 0)
            dim = sk.sketchDimensions.addDistanceDimension(line.startSketchPoint, line.endSketchPoint, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, pt_text)
            
            dim.parameter.expression = "SideLen"
            
            # 3. Run Sort
            # Allow Fusion to update internal dependency graph
            adsk.doEvents()
            
            # We explicitly pass force_map_refresh=True
            handler._auto_sort_params(force_map_refresh=True)
            
            # 4. Verify Comment Update
            # Should be "[SortingBody] Old Comment"
            print(f"DEBUG: Param Comment after sort: {param.comment}")
            self.assertTrue("[SortingBody]" in param.comment, f"Expected '[SortingBody]' in comment, but got: '{param.comment}'")

    def test_units_handling(self):
        """
        Verify that creating parameters respects units (mm vs in).
        """
        with TestContext() as ctx:
            design = ctx.design
            units_mgr = design.unitsManager
            
            # 1. Set doc to Inches
            units_mgr.distanceDisplayUnits = adsk.fusion.DistanceUnits.InchDistanceUnits
            
            # 2. Create param
            params = design.userParameters
            p = params.add("TestInch", adsk.core.ValueInput.createByString("1 in"), "in", "")
            
            # 3. Verify internal value (Fusion uses cm internally)
            # 1 inch = 2.54 cm
            self.assertAlmostEqual(p.value, 2.54, places=4)

    def test_auto_sort_after_creation(self):
        """
        Verify that auto-sort triggers automatically after creating a new parameter via batch_update.
        This tests the fix for the "Unused folder disappearing" bug.
        """
        with TestContext() as ctx:
            design = ctx.design
            root = design.rootComponent
            handler = ZenPaletteEventHandler("TEST_PALETTE", APP_PATH)
            
            # 1. Create a body for context
            sk = root.sketches.add(root.xYConstructionPlane)
            lines = sk.sketchCurves.sketchLines
            lines.addTwoPointRectangle(adsk.core.Point3D.create(0,0,0), adsk.core.Point3D.create(10,10,0))
            prof = sk.profiles.item(0)
            ext = root.features.extrudeFeatures.addSimple(prof, adsk.core.ValueInput.createByReal(2.0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            body = ext.bodies.item(0)
            body.name = "TestBody"
            
            # 2. Simulate creating a new parameter via batch_update (like the UI does)
            batch_data = {
                'items': [
                    {
                        'name': 'NewTestParam',
                        'expression': '15mm',
                        'comment': '',  # Empty comment
                        'isUser': True
                    }
                ],
                'suppress_refresh': False
            }
            
            # 3. Call batch_update handler
            # We pass a mock args object
            class MockArgs:
                def __init__(self):
                    self.data = json.dumps(batch_data)
                    self.returnData = None
            
            handler._handle_batch_update(batch_data, MockArgs())
            
            # 4. Verify parameter was created
            created_param = design.userParameters.itemByName('NewTestParam')
            self.assertIsNotNone(created_param, "Parameter should have been created")
            
            # 5. Verify auto-sort ran (comment should have category tag)
            # Since the param is unused, it should be tagged [Unused]
            comment = created_param.comment
            print(f"DEBUG: Created param comment: '{comment}'")
            self.assertTrue('[Unused]' in comment or '[' in comment, 
                          f"Expected category tag in comment, got: '{comment}'")
            
            # 6. Clean up
            created_param.deleteMe()


# --- TEST RUNNER ---

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Create Suite
        suite = unittest.TestSuite()
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPureLogic))
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFusionIntegration))
        
        # Run
        # We redirect output to a file or string because stdout is generic in Fusion
        log_path = os.path.join(TEST_DIR, 'test_results.txt')
        if not os.path.exists(TEST_DIR): os.makedirs(TEST_DIR)
        
        with open(log_path, 'w') as f:
            runner = unittest.TextTestRunner(stream=f, verbosity=2)
            result = runner.run(suite)
            
        # Report to UI
        msg = f"Tests Run: {result.testsRun}\nErrors: {len(result.errors)}\nFailures: {len(result.failures)}"
        title = "ZenParams Test Results"
        
        # Open the log file for the user
        # os.startfile(log_path) # Windows only
        
        if result.wasSuccessful():
            ui.messageBox(msg, title, adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.InformationIconType)
        else:
            ui.messageBox(msg + "\n\nSee test_results.txt for details.", title, adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.CriticalIconType)
            
    except:
        if ui:
            ui.messageBox('Test Failed:\n{}'.format(traceback.format_exc()))

