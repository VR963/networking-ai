#!/usr/bin/env python3
"""
Generate OpenAPI specification files from FastAPI application.

Exports both JSON and YAML formats for documentation and client generation.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.networking_ai.api.main import app


def generate_openapi_files():
    """Generate OpenAPI specification in JSON and YAML formats."""

    # Get OpenAPI schema from FastAPI
    openapi_schema = app.openapi()

    # Enhance the schema with additional metadata
    openapi_schema["info"]["contact"] = {
        "name": "Networking AI Support",
        "email": "support@networking-ai.com",
        "url": "https://networking-ai.com/support"
    }

    openapi_schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://networking-ai.com/license"
    }

    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.networking-ai.com",
            "description": "Production server"
        },
        {
            "url": "https://staging.networking-ai.com",
            "description": "Staging server"
        }
    ]

    # Add security schemes documentation
    if "components" in openapi_schema and "securitySchemes" in openapi_schema["components"]:
        for scheme_name, scheme in openapi_schema["components"]["securitySchemes"].items():
            if scheme.get("type") == "http" and scheme.get("scheme") == "bearer":
                scheme["description"] = (
                    "JWT Bearer token authentication. "
                    "Obtain token via /api/auth/login or /api/v1/mobile/auth/login. "
                    "Include in Authorization header as: Bearer <token>"
                )

    # Create docs directory if it doesn't exist
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    # Write JSON format
    json_path = docs_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated: {json_path}")

    # Write YAML format
    try:
        import yaml

        yaml_path = docs_dir / "openapi.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(openapi_schema, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"✅ Generated: {yaml_path}")
    except ImportError:
        print("⚠️  PyYAML not installed, skipping YAML generation")
        print("   Install with: pip install pyyaml")

    # Print summary
    print(f"\n📊 OpenAPI Specification Summary:")
    print(f"   Title: {openapi_schema['info']['title']}")
    print(f"   Version: {openapi_schema['info']['version']}")
    print(f"   Endpoints: {len(openapi_schema.get('paths', {}))}")
    print(f"   Schemas: {len(openapi_schema.get('components', {}).get('schemas', {}))}")

    # Count endpoints by tag
    tags_count = {}
    for path, methods in openapi_schema.get("paths", {}).items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "patch", "delete"]:
                tags = details.get("tags", ["Untagged"])
                for tag in tags:
                    tags_count[tag] = tags_count.get(tag, 0) + 1

    print(f"\n📋 Endpoints by Category:")
    for tag, count in sorted(tags_count.items(), key=lambda x: x[1], reverse=True):
        print(f"   {tag}: {count}")

    return openapi_schema


if __name__ == "__main__":
    print("🚀 Generating OpenAPI Specification...\n")
    schema = generate_openapi_files()
    print("\n✅ OpenAPI generation complete!")
