import pandas as pd
import numpy as np
import random

def generate_operational_data(
    rental_data_path="rental_data.csv", 
    output_filename="operational_data.csv"
):
    """
    Generates synthetic operational time-series data for ALL machines
    found in the rental_data.csv file.

    It creates two types of behavior patterns and randomly assigns them:
    1. Normal Behavior: Fluctuating engine load, simulating active work.
    2. Anomalous Behavior: Engine running but with prolonged low load,
       simulating under-utilization.
    """
    print("Generating synthetic operational data for all vehicles...")

    try:
        rental_df = pd.read_csv(rental_data_path)
        equipment_ids = rental_df['EquipmentID'].unique()
    except FileNotFoundError:
        print(f"ERROR: Main data file '{rental_data_path}' not found. Cannot generate operational data.")
        return

    all_vehicle_data = []
    
    # Define the two behavior patterns
    # Pattern 1: Normal, productive work cycle
    work_cycle = np.sin(np.linspace(0, 4 * np.pi, 60)) * 30 + 50
    normal_pattern = np.tile(work_cycle, 2) + np.random.normal(0, 5, 120)
    normal_pattern = np.clip(normal_pattern, 10, 100)
    
    # Pattern 2: Anomalous, under-utilized (prolonged idle)
    anomalous_pattern = np.ones(120) * 15 + np.random.normal(0, 2, 120)
    anomalous_pattern = np.clip(anomalous_pattern, 5, 25)

    # Ensure our two specific examples for the demo are set correctly
    # EX-01 will be our reference "normal" machine for training
    # WL-02 will be our reference "anomalous" machine
    predefined_behaviors = {
        'EX-01': normal_pattern,
        'WL-02': anomalous_pattern
    }

    for i, equipment_id in enumerate(equipment_ids):
        # Set start time to create some variation
        start_time = pd.Timestamp("2025-08-29 08:00") + pd.Timedelta(minutes=i*15)
        dates = pd.to_datetime(pd.date_range(start=start_time, periods=120, freq='min'))

        if equipment_id in predefined_behaviors:
            engine_load = predefined_behaviors[equipment_id]
        else:
            # Randomly assign a behavior to all other machines
            engine_load = random.choice([normal_pattern, anomalous_pattern])
        
        df_vehicle = pd.DataFrame({
            'Timestamp': dates,
            'EquipmentID': equipment_id,
            'EngineLoad': engine_load,
        })
        all_vehicle_data.append(df_vehicle)
    
    # --- Combine and Save ---
    final_df = pd.concat(all_vehicle_data).reset_index(drop=True)
    final_df.to_csv(output_filename, index=False)
    
    print(f"Successfully generated and saved data for {len(equipment_ids)} vehicles to '{output_filename}'.")

if __name__ == "__main__":
    generate_operational_data()