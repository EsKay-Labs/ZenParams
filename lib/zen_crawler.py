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
        Determines the owner body for a parameter by scanning for usage.
        Returns: "BodyName", "Shared", or None.
        """
        if not param.isValid: return None
        
        target_name = param.name
        driven_bodies = set()
        
        try:
            # Reverse-Reverse Indexing:
            # We can't ask a param what uses it.
            # We MUST ask all ModelParameters if they use this param.
            
            # This search could be slow, but for 50-100 user params and ~1000 model params
            # it should be sub-second.
            
            # Pre-compile regex for strict word match
            import re
            pattern = re.compile(rf"\b{re.escape(target_name)}\b")
            
            for model_param in self.design.allParameters:
                # optimization: skip if expression is empty or explicitly static
                if not model_param.expression: continue
                
                # Check for usage
                if pattern.search(model_param.expression):
                    # Found usage! model_param is driven by user_param.
                    # Who owns model_param?
                    
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
                        found_bodies = self.entity_map[target_token]
                        driven_bodies.update(found_bodies)
                        log_diag(f"  MATCH: {target_name} -> {model_param.name} -> {list(found_bodies)}")
                    
                    elif creator and hasattr(creator, 'parentComponent'):
                        # Fallback: If not mapped to a body (e.g. unconsumed sketch),
                        # See if it belongs to a sub-component (not Root).
                        comp = creator.parentComponent
                        root = self.design.rootComponent
                        if comp and comp.name != root.name:
                             driven_bodies.add(comp.name)
                             log_diag(f"  FALLBACK: {target_name} -> Component '{comp.name}'")
                        elif target_token:
                             creator_type = creator.objectType if hasattr(creator, 'objectType') else type(creator).__name__
                             log_diag(f"  MISS: {target_name} -> {creator_type} (Unconsumed in Root)")
                    
                    elif target_token:
                        creator_type = creator.objectType if hasattr(creator, 'objectType') else type(creator).__name__
                        log_diag(f"  MISS: {target_name} -> {model_param.name} [{creator_type}] (Token {target_token[:5]}... not in map)")

        except Exception as e:
            log_diag(f"Param Trace Error: {e}")
        
        # 2. Analyze Results
        if len(driven_bodies) == 0: return None
        if len(driven_bodies) == 1: return list(driven_bodies)[0]
        return "Shared" # Conflict

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
                            body_name = body.name
                            # Map Feature -> Body
                            self._map_entity(feat, body_name)
                            # Map Source Sketch -> Body
                            self._map_feature_to_sketch(feat, body_name)
            
            log_diag(f"Crawler Map Built: {len(self.entity_map)} entities mapped.")

        except Exception as e:
            log_diag(f"Crawler Map Error: {e}")

    def _map_entity(self, entity, body_name):
        try:
            token = entity.entityToken
            if token not in self.entity_map:
                self.entity_map[token] = set()
            self.entity_map[token].add(body_name)
        except: pass

    def _map_feature_to_sketch(self, feat, body_name):
        # Extract profiles/points to find the sketch
        try:
            # 1. Profile-based (Extrude, Revolve, Sweep, Loft)
            if hasattr(feat, 'profile'): 
                profile = feat.profile
                if profile:
                    # Single Profile
                    if isinstance(profile, adsk.fusion.Profile):
                        self._map_entity(profile.parentSketch, body_name)
                        log_diag(f"    Mapped Sketch {profile.parentSketch.entityToken[:5]}... -> {body_name}")
                    # Profile Collection
                    elif hasattr(profile, 'count'): 
                        for k in range(profile.count):
                            item = profile.item(k)
                            if isinstance(item, adsk.fusion.Profile):
                                self._map_entity(item.parentSketch, body_name)
                                log_diag(f"    Mapped Sketch {item.parentSketch.entityToken[:5]}... -> {body_name}")
                                
            # 2. Hole Feature (Uses sketchPoints)
            if isinstance(feat, adsk.fusion.HoleFeature):
                # Hole can be placed by SketchPoints or Non-Sketch
                points = feat.sketchPoints
                if points and points.count > 0:
                    pt = points.item(0)
                    if hasattr(pt, 'parentSketch'):
                         self._map_entity(pt.parentSketch, body_name)
                         
             # 3. Emboss (Uses sketchProfiles)
            if isinstance(feat, adsk.fusion.EmbossFeature):
                 profs = feat.sketchProfiles
                 if profs and profs.count > 0:
                     p = profs.item(0)
                     if isinstance(p, adsk.fusion.Profile):
                         self._map_entity(p.parentSketch, body_name)

        except: pass

    def get_driven_bodies(self, param):
        # Legacy/Debug wrapper
        name = self.get_param_body_name(param)
        return [name] if name else []
