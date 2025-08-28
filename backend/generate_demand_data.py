import pandas as pd
import numpy as np

# --- Configuration ---
N_YEARS = 5
START_DATE = "2020-01-01"
END_DATE = str(int(START_DATE[:4]) + N_YEARS - 1) + "-12-31"
FILENAME = "demand_data.csv"

def generate_demand_data():
    """
    Generates a synthetic time-series dataset for equipment rental demand.
    The dataset includes trend, yearly seasonality, weekly seasonality, and noise.
    """
    # Create a date range
    dates = pd.to_datetime(pd.date_range(start=START_DATE, end=END_DATE, freq='D'))
    n_days = len(dates)

    # --- Component 1: Trend ---
    # A steady, slightly accelerating growth in demand over time
    trend = np.linspace(50, 150, n_days) + np.linspace(0, 50, n_days)**1.1

    # --- Component 2: Yearly Seasonality (e.g., construction season) ---
    # Higher demand in the middle of the year
    day_of_year = dates.dayofyear
    yearly_seasonality = 25 * (1 + np.sin(2 * np.pi * (day_of_year - 90) / 365.25))

    # --- Component 3: Weekly Seasonality ---
    # Lower demand on weekends
    day_of_week = dates.dayofweek
    weekly_seasonality = -15 * (1 - np.cos(2 * np.pi * (day_of_week) / 7))
    # Make Sunday the lowest
    weekly_seasonality[day_of_week == 6] *= 1.5

    # --- Component 4: Noise ---
    # Random fluctuations in demand
    noise = np.random.normal(0, 10, n_days)

    # --- Combine Components ---
    # The final demand is the sum of all components, ensuring it's non-negative
    demand = trend + yearly_seasonality + weekly_seasonality + noise
    demand[demand < 0] = 0

    # --- Create DataFrame ---
    df = pd.DataFrame({
        'ds': dates,
        'y': np.round(demand).astype(int) # 'ds' and 'y' are required column names for Prophet
    })

    # --- Save to CSV ---
    df.to_csv(FILENAME, index=False)
    print(f"Successfully generated and saved '{FILENAME}' with {len(df)} records.")

if __name__ == "__main__":
    generate_demand_data()