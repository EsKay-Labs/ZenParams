import adsk.core, adsk.fusion
import traceback
from .zen_utils import log_diag

class ZenDependencyCrawler:
    """
    Analyzes parameter dependencies to find what geometry they drive.
    Used for Auto-Categorization.
    """
    def __init__(self, design):
        self.design = design
        self.entity_map = {} # { entity_token: set(body_names) }
        self.refresh_map()

    def refresh_map(self):
        """
        Rebuilds the reverse map. Call this when new geometry is created.
        """
        self.entity_map = {}
        self._build_reverse_map()

    def get_param_body_name(self, param):
        """
        Determines the owner body(ies) for a parameter by scanning for usage.
        Returns: 
            - None if no usage found (Unused)
            - ["ComponentName/BodyName"] if used by exactly one body
            - ["Comp1/Body1", "Comp2/Body2", ...] if used by multiple bodies (Shared)
        """
        if not param.isValid: return None
        
        target_name = param.name
        driven_paths = set()  # Changed from driven_bodies
        
        try:
            # Reverse-Reverse Indexing:
            # We can't ask a param what uses it.
            # We MUST ask all ModelParameters if they use this param.
            
            import re
            pattern = re.compile(rf"\b{re.escape(target_name)}\b")
            
            for model_param in self.design.allParameters:
                if not model_param.expression: continue
                
                if pattern.search(model_param.expression):
                    creator = model_param.createdBy
                    if not creator or not creator.isValid: continue
                    
                    target_token = None
                    
                    # 1. Sketch Dimension
                    if isinstance(creator, adsk.fusion.SketchDimension):
                         if hasattr(creator, 'parentSketch'):
                            target_token = creator.parentSketch.entityToken
                         elif hasattr(creator, 'sketch'):
                            target_token = creator.sketch.entityToken
                            
                    # 2. Feature
                    elif isinstance(creator, adsk.fusion.Feature):
                        target_token = creator.entityToken
                        
                    # 3. Generic
                    elif hasattr(creator, 'entityToken'):
                        target_token = creator.entityToken

                    if target_token and target_token in self.entity_map:
                        found_paths = self.entity_map[target_token]
                        driven_paths.update(found_paths)
                        log_diag(f"  MATCH: {target_name} -> {model_param.name} -> {list(found_paths)}")
                    
                    elif creator and hasattr(creator, 'parentComponent'):
                        comp = creator.parentComponent
                        if comp:
                             # Map to component only (no body)
                             path = comp.name
                             driven_paths.add(path)
                             log_diag(f"  FALLBACK: {target_name} -> Component '{path}'")
                    
                    elif target_token:
                        creator_type = creator.objectType if hasattr(creator, 'objectType') else type(creator).__name__
                        log_diag(f"  MISS: {target_name} -> {model_param.name} [{creator_type}] (Token not in map)")

        except Exception as e:
            log_diag(f"Param Trace Error: {e}")
        
        # Prune redundant paths (e.g. if we have "Comp" and "Comp/Body", remove "Comp")
        # This fixes the issue where Sketch-on-Origin parameters are marked as Shared
        # because they map to both the Component (Fallback) and the Body (Feature Usage).
        final_paths = set(driven_paths)
        for p in driven_paths:
            # If p is a prefix of any other path (implied parent), remove it
            # We look for "p/" to ensure it acts as a folder
            is_redundant = any(other.startswith(p + "/") for other in driven_paths)
            if is_redundant:
                final_paths.discard(p)
                
        if len(final_paths) == 0: 
            return None
        return list(final_paths)

    def _build_reverse_map(self):
        """
        Scans the design to find which Features/Sketches own which Bodies.
        Populates self.entity_map.
        Uses Timeline iteration because body.creationFeature is unreliable.
        """
        try:
            timeline = self.design.timeline
            # count = timeline.count
            # log_diag(f"Scanning {count} timeline objects...")
            
            for i in range(timeline.count):
                obj = timeline.item(i)
                # obj is a TimelineObject. entity returns the Feature (e.g. ExtrudeFeature)
                feat = obj.entity
                
                if not feat or not feat.isValid: continue
                
                # Debug: Audit Feature Types
                feat_type = feat.objectType.split('::')[-1]
                log_diag(f"Timeline Item {i}: {feat_type}")
                
                # We are looking for features that produce bodies
                # e.g. Extrude, Revolve, Sweep, Loft, Thicken, etc.
                if hasattr(feat, 'bodies') and feat.bodies.count > 0:
                    for k in range(feat.bodies.count):
                        body = feat.bodies.item(k)
                        if body and body.isValid:
                            # Build Component/Body path
                            comp_name = body.parentComponent.name if body.parentComponent else "Root"
                            path = f"{comp_name}/{body.name}"
                            # Map Feature -> Path
                            self._map_entity(feat, path)
                            # Map Source Sketch -> Path
                            self._map_feature_to_sketch(feat, path)
                
                # Special Case: Sketch created ON a Body Face
                # Even if not extruded yet, it belongs to that Body.
                if isinstance(feat, adsk.fusion.Sketch):
                    try:
                        is_mapped = False
                        plane = feat.referencePlane
                        if isinstance(plane, adsk.fusion.BRepFace):
                            body = plane.body
                            if body and body.isValid:
                                comp_name = body.parentComponent.name if body.parentComponent else "Root"
                                path = f"{comp_name}/{body.name}"
                                self._map_entity(feat, path)
                                log_diag(f"  Mapped Sketch-on-Face {feat.name} -> {path}")
                                is_mapped = True
                        
                        # Fallback: Map to component only (e.g. Sketch on Origin Plane)
                        if not is_mapped and feat.parentComponent:
                            comp_name = feat.parentComponent.name
                            self._map_entity(feat, comp_name)  # Just component, no body
                            log_diag(f"  Mapped Sketch (Generic) {feat.name} -> {comp_name}")

                    except: pass
            
            log_diag(f"Crawler Map Built: {len(self.entity_map)} entities mapped.")

        except Exception as e:
            log_diag(f"Crawler Map Error: {e}")

    def _map_entity(self, entity, path):
        try:
            token = entity.entityToken
            if token not in self.entity_map:
                self.entity_map[token] = set()
            self.entity_map[token].add(path)
        except: pass

    def _map_feature_to_sketch(self, feat, path):
        # Extract profiles/points to find the sketch
        try:
            # 1. Profile-based (Extrude, Revolve, Sweep, Loft)
            if hasattr(feat, 'profile'): 
                profile = feat.profile
                if profile:
                    # Single Profile
                    if isinstance(profile, adsk.fusion.Profile):
                        self._map_entity(profile.parentSketch, path)
                        log_diag(f"    Mapped Sketch {profile.parentSketch.entityToken[:5]}... -> {path}")
                    # Profile Collection
                    elif hasattr(profile, 'count'): 
                        for k in range(profile.count):
                            item = profile.item(k)
                            if isinstance(item, adsk.fusion.Profile):
                                self._map_entity(item.parentSketch, path)
                                log_diag(f"    Mapped Sketch {item.parentSketch.entityToken[:5]}... -> {path}")
                                
            # 2. Hole Feature (Uses sketchPoints)
            if isinstance(feat, adsk.fusion.HoleFeature):
                # Hole can be placed by SketchPoints or Non-Sketch
                points = feat.sketchPoints
                if points and points.count > 0:
                    pt = points.item(0)
                    if hasattr(pt, 'parentSketch'):
                         self._map_entity(pt.parentSketch, path)
                         
             # 3. Emboss (Uses sketchProfiles)
            if isinstance(feat, adsk.fusion.EmbossFeature):
                 profs = feat.sketchProfiles
                 if profs and profs.count > 0:
                     p = profs.item(0)
                     if isinstance(p, adsk.fusion.Profile):
                         self._map_entity(p.parentSketch, path)

        except: pass

    def get_driven_bodies(self, param):
        # Legacy/Debug wrapper
        name = self.get_param_body_name(param)
        return [name] if name else []
