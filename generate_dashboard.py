import pandas as pd
import os
import glob

# Change to load from 'hourly_index_monthly_picks.csv'
file_path = 'hourly_index_monthly_picks.csv'

# Function to load the data with error handling
def load_data(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    # You can add any other checks needed here (e.g., file format)
    return pd.read_csv(file_path)

try:
    data = load_data(file_path)
    print(data)
except FileNotFoundError as e:
    print(e)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    
# Additional code for processing data
# ...