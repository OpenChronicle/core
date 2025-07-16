import os
import yaml

STORYPACKS_DIR = os.path.join(os.getcwd(), "storypacks")


def list_storypacks():
    """List all valid storypacks with meta.yaml."""
    storypacks = []
    for name in os.listdir(STORYPACKS_DIR):
        path = os.path.join(STORYPACKS_DIR, name)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "meta.yaml")):
            storypacks.append(name)
    return storypacks


def load_meta(path):
    """Load meta.yaml contents."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_storypack(name):
    """Load a storypack by folder name."""
    path = os.path.join(STORYPACKS_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Storypack '{name}' not found in {STORYPACKS_DIR}")

    meta_path = os.path.join(path, "meta.yaml")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"meta.yaml missing in storypack '{name}'")

    meta = load_meta(meta_path)

    return {
        "id": name,
        "path": path,
        "meta": meta,
        "canon_dir": os.path.join(path, "canon"),
        "characters_dir": os.path.join(path, "characters"),
        "memory_dir": os.path.join(path, "memory"),
        "style_guide": os.path.join(path, "style_guide.md"),
    }