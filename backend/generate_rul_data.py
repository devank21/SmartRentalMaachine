import pandas as pd
import numpy as np

def generate_rul_data(output_filename="rul_data.csv", n_machines=5, max_life_cycles=250):
    """
    Generates a synthetic dataset for Remaining Useful Life (RUL) prediction.

    This function simulates sensor data from multiple machines that degrade over time.
    The degradation is linear, with added noise to make it more realistic.

    Args:
        output_filename (str): The name of the CSV file to save the data.
        n_machines (int): The number of machines to simulate.
        max_life_cycles (int): The maximum number of operational cycles (hours) for any machine.
    """
    print("Generating synthetic RUL training data...")
    
    all_machine_data = []

    for i in range(1, n_machines + 1):
        # Each machine has a slightly different total lifespan
        lifespan = max_life_cycles - np.random.randint(20, 50)
        
        machine_id = f"MC-{1000 + i}"
        cycles = np.arange(1, lifespan + 1)
        
        # --- Feature Engineering Simulation ---
        # Simulate sensor readings that degrade over time
        
        # Vibration (RMS) - starts low, increases steadily
        vibration_rms = 0.1 + (cycles / lifespan) * 2.0 + np.random.normal(0, 0.05, lifespan)
        
        # Temperature - starts normal, increases sharply towards the end of life
        temp_increase_factor = (cycles / lifespan) ** 3
        temperature = 80 + temp_increase_factor * 40 + np.random.normal(0, 1.5, lifespan)
        
        # Rotational Speed - should be stable but gets slightly more erratic
        rotational_speed = 1500 + np.random.normal(0, 2 + (cycles / lifespan) * 10, lifespan)

        # Create a DataFrame for this machine
        df_machine = pd.DataFrame({
            'MachineID': machine_id,
            'Cycle': cycles,
            'VibrationRMS': vibration_rms,
            'Temperature': temperature,
            'RotationalSpeed': rotational_speed
        })
        
        # --- Label Creation (The RUL) ---
        # The RUL is the total lifespan minus the current cycle
        df_machine['RUL'] = lifespan - df_machine['Cycle']
        
        all_machine_data.append(df_machine)

    # Combine all data and save to CSV
    final_df = pd.concat(all_machine_data).reset_index(drop=True)
    final_df.to_csv(output_filename, index=False)
    
    print(f"Successfully generated and saved RUL data for {n_machines} machines to '{output_filename}'.")

if __name__ == "__main__":
    generate_rul_data()