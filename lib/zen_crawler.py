import adsk.core, adsk.fusion
import traceback
import re
from .zen_utils import log_diag

class ZenDependencyCrawler:
    """
    Analyzes parameter dependencies to find what geometry they drive.
    OPTIMIZED (v2): Uses Forward-Indexing O(N) instead of Matrix Scan O(NxM).
    """
    def __init__(self, design):
        self.design = design
        self.entity_map = {} # { entity_token: set(body_names) }
        self.dependency_index = {} # { user_param_name: set(owner_tokens) }
        self.refresh_map()

    def refresh_map(self):
        """
        Rebuilds the reverse map. Call this when new geometry is created.
        """
        self.entity_map = {}
        self.dependency_index = {}
        self._build_reverse_map()
        self._build_dependency_index()

    def get_param_body_name(self, param):
        """
        Determines the owner body(ies) for a parameter using the index.
        Returns: 
            - None if no usage found (Unused)
            - ["ComponentName/BodyName"] if used by exactly one body
            - ["Comp1/Body1", "Comp2/Body2", ...] if used by multiple bodies (Shared)
        """
        if not param.isValid: return None
        
        target_name = param.name
        
        # O(1) Lookup (Forward Index)
        if target_name not in self.dependency_index:
            return None
            
        token_list = self.dependency_index[target_name]
        driven_paths = set()
        
        for token in token_list:
            if token in self.entity_map:
                found_paths = self.entity_map[token]
                driven_paths.update(found_paths)
            
            # NOTE: We can add fallbacks here (like component mapping) if the token 
            # isn't mapped to a body but is mapped to a component concept.
            # For now, we stick to the Body-Level mapping which is what entity_map provides.

        # Prune redundant paths (e.g. if we have "Comp" and "Comp/Body", remove "Comp")
        final_paths = set(driven_paths)
        for p in driven_paths:
            is_redundant = any(other.startswith(p + "/") for other in driven_paths)
            if is_redundant:
                final_paths.discard(p)
                
        if len(final_paths) == 0: 
            return None
        return list(final_paths)

    def _build_dependency_index(self):
        """
        Scans ALL Model Parameters ONCE to find which User Parameters they use.
        Populates self.dependency_index.
        """
        try:
            # 1. Get all User Param names set for O(1) checking
            user_param_names = set([p.name for p in self.design.userParameters])
            if not user_param_names: return

            # 2. Regex for variable extraction
            # Matches valid fusion param names: letters, numbers, underscores
            var_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')
            
            # 3. Iterate ALL parameters ONCE
            for model_param in self.design.allParameters:
                if not model_param.expression: continue
                
                # Check for usage
                refs = set(var_pattern.findall(model_param.expression))
                found_params = refs.intersection(user_param_names)
                
                if not found_params: continue
                
                # Found usage! Now identify the Owner Entity
                owner_token = self._get_owner_token(model_param)
                if not owner_token: continue
                
                # Record in Index
                for p_name in found_params:
                    if p_name not in self.dependency_index:
                        self.dependency_index[p_name] = set()
                    self.dependency_index[p_name].add(owner_token)

            # log_diag(f"Dependency Index Built: {len(self.dependency_index)} active user params.")

        except Exception as e:
            log_diag(f"Index Build Error: {e}")

    def _get_owner_token(self, model_param):
        """Trace back a model parameter to its owning entity."""
        try:
            creator = model_param.createdBy
            if not creator or not creator.isValid: return None
            
            # 1. Sketch Dimension -> Sketch
            if isinstance(creator, adsk.fusion.SketchDimension):
                 if hasattr(creator, 'parentSketch'): return creator.parentSketch.entityToken
                 elif hasattr(creator, 'sketch'): return creator.sketch.entityToken
            
            # 2. Feature
            elif isinstance(creator, adsk.fusion.Feature):
                return creator.entityToken
                
            # 3. Generic
            elif hasattr(creator, 'entityToken'):
                return creator.entityToken
                
            return None
        except: return None

    def _build_reverse_map(self):
        """
        Scans the design to find which Features/Sketches own which Bodies.
        Populates self.entity_map.
        """
        try:
            timeline = self.design.timeline
            for i in range(timeline.count):
                obj = timeline.item(i)
                feat = obj.entity
                if not feat or not feat.isValid: continue
                
                # Features that produce bodies
                if hasattr(feat, 'bodies') and feat.bodies.count > 0:
                    for k in range(feat.bodies.count):
                        body = feat.bodies.item(k)
                        if body and body.isValid:
                            comp_name = body.parentComponent.name if body.parentComponent else "Root"
                            path = f"{comp_name}/{body.name}"
                            self._map_entity(feat, path)
                            self._map_feature_to_sketch(feat, path)
                
                # Sketch on Face logic
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
                                is_mapped = True
                        
                        # Fallback: Component mapping
                        if not is_mapped and feat.parentComponent:
                            self._map_entity(feat, feat.parentComponent.name)
                    except: pass
            
            # log_diag(f"Crawler Map Built: {len(self.entity_map)} entities mapped.")

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
        try:
            # 1. Profile-based
            if hasattr(feat, 'profile'): 
                profile = feat.profile
                if profile:
                    if isinstance(profile, adsk.fusion.Profile):
                        self._map_entity(profile.parentSketch, path)
                    elif hasattr(profile, 'count'): 
                        for k in range(profile.count):
                            item = profile.item(k)
                            if isinstance(item, adsk.fusion.Profile):
                                self._map_entity(item.parentSketch, path)
                                
            # 2. Hole Feature
            if isinstance(feat, adsk.fusion.HoleFeature):
                points = feat.sketchPoints
                if points and points.count > 0:
                    pt = points.item(0)
                    if hasattr(pt, 'parentSketch'):
                         self._map_entity(pt.parentSketch, path)
                         
             # 3. Emboss
            if isinstance(feat, adsk.fusion.EmbossFeature):
                 profs = feat.sketchProfiles
                 if profs and profs.count > 0:
                     p = profs.item(0)
                     if isinstance(p, adsk.fusion.Profile):
                         self._map_entity(p.parentSketch, path)
        except: pass

    def get_driven_bodies(self, param):
        name = self.get_param_body_name(param)
        return [name] if name else []
