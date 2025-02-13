import os
import shutil
import subprocess

# Define paths
outputs_dir = 'outputs'
fmp_data_dir = os.path.join(outputs_dir, 'fmp_data')

# Delete all files in the 'outputs/' directory if it exists
if os.path.exists(outputs_dir):
    for filename in os.listdir(outputs_dir):
        file_path = os.path.join(outputs_dir, filename)
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Remove directories
            else:
                os.remove(file_path)  # Remove files
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

# Create 'outputs/fmp_data/' directory if it doesn't exist
os.makedirs(fmp_data_dir, exist_ok=True)

# Run the Streamlit chatbot.py app
subprocess.run(['streamlit', 'run', 'chatbot.py'])
