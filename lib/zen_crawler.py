import adsk.core, adsk.fusion
import traceback

class ZenDependencyCrawler:
    """
    Analyzes parameter dependencies to find what geometry they drive.
    Used for Auto-Categorization.
    """
    def __init__(self, design):
        self.design = design

    def get_param_body_name(self, param):
        """
        Helper to return the name of the first driven body found, or None.
        """
        bodies = self.get_driven_bodies(param)
        if bodies:
            return bodies[0]
        return None

    def get_driven_bodies(self, param):
        """
        Traces a parameter to find which bodies it affects.
        Returns a list of unique body names (e.g. ['Enclosure', 'Lid']).
        """
        driven_bodies = set()
        
        try:
            # 1. Direct Dependency Check
            # Warning: specific API calls can be heavy, check strictly necessary props
            if not param.isValid: return []

            # dependentDependencies returns a Dependencies collection
            deps = param.dependentDependencies
            
            for i in range(deps.count):
                dep = deps.item(i)
                entity = dep.entity
                
                # CASE A: Parameter drives a Feature (Extrude, Revolve, etc.)
                if isinstance(entity, adsk.fusion.Feature):
                    # Check if feature has bodies
                    if hasattr(entity, 'bodies') and entity.bodies.count > 0:
                        for j in range(entity.bodies.count):
                            body = entity.bodies.item(j)
                            if body.isValid and body.name:
                                driven_bodies.add(body.name)
                
                # CASE B: Parameter drives a Sketch Dimension?
                # (Future Complexity: Sketch -> Profile -> Feature -> Body)
                # For now, we skip deep recursion to keep it fast ("Overkill" but efficient)
        
        except:
            # Logging requires a way to communicate back, for now just fail safe
            pass
            
        return list(driven_bodies)
