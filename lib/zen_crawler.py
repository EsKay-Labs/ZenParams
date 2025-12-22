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
        self._build_reverse_map()

    def get_param_body_name(self, param):
        """
        Determines the owner body for a parameter using the reverse map.
        Returns:
            - "BodyName" (if single match)
            - "Shared" (if multiple bodies)
            - None (if no link found)
        """
        if not param.isValid: return None
        
        # 1. Trace immediate dependencies
        # A param might drive: SketchDimension, FeatureInput, etc.
        driven_bodies = set()
        
        try:
            deps = param.dependentDependencies
            for i in range(deps.count):
                dep = deps.item(i)
                entity = dep.entity
                
                if not entity or not entity.isValid: continue

                # Resolve the "Real" Entity that has the geometry
                # e.g. SketchDimension -> OwnerSketch
                target_token = None
                
                if isinstance(entity, adsk.fusion.SketchDimension):
                    target_token = entity.sketch.entityToken
                elif isinstance(entity, adsk.fusion.Feature):
                    target_token = entity.entityToken
                elif hasattr(entity, 'entityToken'):
                    target_token = entity.entityToken
                
                # trace log?
                # log_diag(f"  Param {param.name} -> {type(entity)} -> {target_token}")

                if target_token and target_token in self.entity_map:
                    found_bodies = self.entity_map[target_token]
                    driven_bodies.update(found_bodies)
                    
        except: pass
        
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

        except Exception as e:
            log_diag(f"Crawler Map Error: {e}")

    def _map_entity(self, entity, body_name):
        token = entity.entityToken
        if token not in self.entity_map:
            self.entity_map[token] = set()
        self.entity_map[token].add(body_name)

    def _map_feature_to_sketch(self, feat, body_name):
        # Extract profiles to find the sketch
        # Supported: Extrude, Revolve, Sweep, Loft
        try:
            # Common property: 'profile' (Input or Object)
            # ExtrudeFeature -> profile
            profile = None
            if hasattr(feat, 'profile'): 
                profile = feat.profile
            # RevolveFeature -> profile
            
            if profile:
                # If it's a Profile object, it has a parentSketch
                if isinstance(profile, adsk.fusion.Profile):
                    self._map_entity(profile.parentSketch, body_name)
                # If it's a collection of profiles (ProfileWrapper? ObjectCollection?)
                elif hasattr(profile, 'count'): # Collection
                    for k in range(profile.count):
                        item = profile.item(k)
                        if isinstance(item, adsk.fusion.Profile):
                            self._map_entity(item.parentSketch, body_name)
        except: pass

    def get_driven_bodies(self, param):
        # Legacy/Debug wrapper
        name = self.get_param_body_name(param)
        return [name] if name else []
