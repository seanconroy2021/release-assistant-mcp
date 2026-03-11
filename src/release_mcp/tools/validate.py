"""Validation tools."""

import json

import jsonschema


def register_validate_tools(mcp, index):

    @mcp.tool()
    def validate(data_json: str) -> str:
        """Validate JSON against the dataKeys schema.

        Args:
            data_json: JSON string to validate.
        """
        if index.schema is None:
            return "Schema not loaded."

        try:
            data = json.loads(data_json)
        except json.JSONDecodeError as exc:
            return f"Invalid JSON: {exc}"

        try:
            jsonschema.validate(instance=data, schema=index.schema)
            return "Validation passed."
        except jsonschema.ValidationError as exc:
            path = " -> ".join(str(p) for p in exc.absolute_path) or "(root)"
            return f"Validation failed at [{path}]:\n  {exc.message}"
        except jsonschema.SchemaError as exc:
            return f"Schema error: {exc.message}"

    @mcp.tool()
    def schema(path: str = "") -> str:
        """Show the dataKeys schema or a sub-path.

        Args:
            path: Dot-separated path (e.g. 'properties.advisory'). Empty for full schema.
        """
        if index.schema is None:
            return "Schema not loaded."

        target = index.schema
        if path:
            for key in path.split("."):
                if isinstance(target, dict) and key in target:
                    target = target[key]
                else:
                    keys = list(target.keys()) if isinstance(target, dict) else "n/a"
                    return f"Path '{path}' not found. Keys: {keys}"

        out = json.dumps(target, indent=2)
        if len(out) > 5000:
            out = out[:5000] + "\n... (truncated)"
        return out
