import os
import sys
import importlib.util

# Get the absolute path to the google_sheets.py file
current_dir = os.path.dirname(os.path.abspath(__file__))
google_sheets_path = os.path.join(current_dir, 'google', 'google_sheets.py')

# Import the module using spec
spec = importlib.util.spec_from_file_location("google_sheets_module", google_sheets_path)
google_sheets_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(google_sheets_module)

# Export the google_sheets function
google_sheets = google_sheets_module.google_sheets 