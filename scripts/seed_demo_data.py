import sys
from pathlib import Path

# Add the project root to path so we can import the app modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.remove_demo_virtual_account import remove_demo_virtual_account


def cleanup_demo_accounts():
    remove_demo_virtual_account()


if __name__ == "__main__":
    cleanup_demo_accounts()