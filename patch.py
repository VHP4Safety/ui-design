from importlib import import_module
from pathlib import Path

def apply_patch():
    try:
        # Dynamically import the module and get its file path
        try:
            module = import_module('pyshexc.parser.ShExDocLexer')
        except ModuleNotFoundError as e:
            # Give a precise, actionable hint for installation in the active interpreter
            print(
                "Missing dependency: 'pyshexc' (PyShExC).\n"
                "Install it in the same environment you're using to run this script.\n"
                "Examples:\n"
                "  python -m pip install PyShExC\n"
                "  # or with uv:   uv pip install PyShExC\n"
                "  # or poetry:    poetry add PyShExC\n"
                "  # or conda:     conda install -c conda-forge pyshexc\n"
            )
            return

        file_path = Path(module.__file__)

        if not file_path.exists():
            raise FileNotFoundError(f"Could not find the file: {file_path}")

        # Read the file content
        file_content = file_path.read_text()

        # Replace 'from typing.io import TextIO' with 'from typing import TextIO'
        new_content = file_content.replace("from typing.io import TextIO", "from typing import TextIO")

        # Only write if a change is needed
        if new_content != file_content:
            file_path.write_text(new_content)
            print("Patch applied successfully!")
        else:
            print("No patch needed; target text not found (already patched or different version).")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    apply_patch()
