# Direct-file execution support; prefer python -m scripts.<group>.<name>.
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

"""Report presence only; never print any part of a secret."""
import os
from mentoring.config import load_environment

def main():
    load_environment()
    for name in ("NOTION_TOKEN", "GEMINI_API_KEY"):
        print(f"{name} present: {bool(os.getenv(name))}")

if __name__ == "__main__":
    main()
