import os
import shutil
import subprocess

# Define paths
outputs_dir = 'outputs'
fmp_data_dir = os.path.join(outputs_dir, 'fmp_data')
valuation_dir = os.path.join(fmp_data_dir, 'valuation')
metrics_dir = os.path.join(fmp_data_dir, 'metrics')

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

# Create 'outputs/fmp_data/', 'outputs/fmp_data/valuation', and 'outputs/fmp_data/metrics' directories if they don't exist
os.makedirs(valuation_dir, exist_ok=True)
os.makedirs(metrics_dir, exist_ok=True)

# Run the Streamlit chatbot.py app
subprocess.run(['streamlit', 'run', 'chatbot.py'])
