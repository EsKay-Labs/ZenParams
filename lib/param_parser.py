import re

class ParamParser:
    """Parses string inputs into Fusion 360 parameter definitions."""

    @staticmethod
    def parse(input_str: str):
        """Parses a command string 'name = expression # comment'.

        Args:
            input_str: The raw input string from the console.

        Returns:
            dict: {
                'name': str,
                'expression': str,
                'comment': str (optional),
                'error': str (optional)
            }
        """
        if not input_str or not input_str.strip():
            return {'error': 'Empty input'}

        # Split comment first
        parts = input_str.split('#', 1)
        main_part = parts[0].strip()
        comment = parts[1].strip() if len(parts) > 1 else ""

        # Check for assignment
        if '=' not in main_part:
            return {'error': "Missing '='. Format: name = value"}

        name_part, expr_part = main_part.split('=', 1)
        
        name = name_part.strip()
        expression = expr_part.strip()

        # Basic validation
        if not name:
            return {'error': 'Missing name'}
        if not expression:
            return {'error': 'Missing value'}
            
        # Validate name (Fusion parameters must be alphanumeric, start with letter)
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            return {'error': f"Invalid name '{name}'. Must start with letter and contain only letters, numbers, or _."}

        return {
            'name': name,
            'expression': expression,
            'comment': comment
        }
