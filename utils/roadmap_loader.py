import os

def load_roadmap():
    """
    Automatically detect and load the correct roadmap file.
    Priority:
      1. Final Roadmap.md
      2. UNIFIED_PROJECT_ROADMAP.md
    Returns the content and the file path used.
    """
    candidates = [
        "Final Roadmap.md",
        "UNIFIED_PROJECT_ROADMAP.md"
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read().strip()
            return {
                "source": candidate,
                "content": content
            }

    # fallback if neither file found
    return {
        "source": None,
        "content": "⚠️ No roadmap file detected. Proceed with mission context only."
    }

# Example usage when initializing the agent
if __name__ == "__main__":
    roadmap = load_roadmap()
    print(f"Loaded: {roadmap['source']}")
    print(roadmap['content'][:500])
