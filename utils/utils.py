# utils/utils.py

import os


def save_to_file(filepath: str, content: str):
    """Saves the given content to a file.

    Args:
        filepath (str): The path to the file.
        content (str): The content to save.
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w") as f:
        f.write(content)
