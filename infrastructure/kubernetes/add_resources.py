#!/usr/bin/env python3
from pathlib import Path

import yaml


def add_resources_to_deployment(file_path):
    """Add resource limits to deployment if missing."""
    with open(file_path, "r") as f:
        docs = list(yaml.safe_load_all(f))

    modified = False
    for doc in docs:
        if doc and doc.get("kind") == "Deployment":
            containers = (
                doc.get("spec", {})
                .get("template", {})
                .get("spec", {})
                .get("containers", [])
            )
            for container in containers:
                if "resources" not in container:
                    container["resources"] = {
                        "requests": {"memory": "256Mi", "cpu": "250m"},
                        "limits": {"memory": "512Mi", "cpu": "500m"},
                    }
                    modified = True

                # Add liveness and readiness probes if missing
                if "livenessProbe" not in container:
                    container["livenessProbe"] = {
                        "httpGet": {"path": "/health", "port": 8080},
                        "initialDelaySeconds": 30,
                        "periodSeconds": 10,
                    }
                    modified = True

                if "readinessProbe" not in container:
                    container["readinessProbe"] = {
                        "httpGet": {"path": "/ready", "port": 8080},
                        "initialDelaySeconds": 10,
                        "periodSeconds": 5,
                    }
                    modified = True

    if modified:
        with open(file_path, "w") as f:
            yaml.dump_all(docs, f, default_flow_style=False, sort_keys=False)
        return True
    return False


if __name__ == "__main__":
    # Process all deployment files
    base_dir = Path("kubernetes/base")
    for file_path in base_dir.glob("*-deployment.yaml"):
        if add_resources_to_deployment(file_path):
            print(f"Added resources to {file_path}")
