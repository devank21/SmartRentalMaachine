import pandas as pd
import numpy as np

def generate_demand_data(
    start_date="2022-01-01",
    end_date="2025-12-31",
    filename="demand_data.csv"
):
    """
    Generates a synthetic demand dataset for rental equipment.

    This function creates a time series dataset with daily demand values,
    incorporating trend, weekly and annual seasonalities, and random noise
    to simulate real-world rental demand patterns.

    Args:
        start_date (str): The start date for the dataset in 'YYYY-MM-DD' format.
        end_date (str): The end date for the dataset in 'YYYY-MM-DD' format.
        filename (str): The name of the CSV file to save the generated data.
    """
    # Create a date range
    dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D'))
    n_days = len(dates)

    # --- 1. Trend Component ---
    # A gentle upward trend simulating business growth
    trend = np.linspace(start=100, stop=150, num=n_days)

    # --- 2. Seasonality Components ---
    # Weekly seasonality: Lower demand on weekends, higher on weekdays
    day_of_week = dates.dayofweek
    weekly_seasonality = np.ones(n_days)  # Start with a base of 1
    weekly_seasonality[day_of_week < 5] = 1.2  # Weekday boost
    weekly_seasonality[day_of_week >= 5] = 0.8 # Weekend dip

    # Annual seasonality: Higher demand in spring/summer, lower in winter
    day_of_year = dates.dayofyear
    annual_seasonality = 1 + 0.3 * np.sin(2 * np.pi * (day_of_year - 80) / 365.25)

    # --- 3. Noise Component ---
    # Random fluctuations to make the data more realistic
    noise = np.random.normal(loc=0, scale=15, size=n_days)

    # --- Combine Components ---
    # Combine trend, seasonalities, and noise to get the final demand
    demand = trend * weekly_seasonality * annual_seasonality + noise
    # Ensure demand is non-negative
    demand = np.maximum(demand, 0).astype(int)

    # --- Create DataFrame and Save ---
    df = pd.DataFrame({'ds': dates, 'y': demand})
    df.to_csv(filename, index=False)
    print(f"Successfully generated synthetic demand data and saved to '{filename}'.")
    print(f"Dataset contains {len(df)} records from {start_date} to {end_date}.")

if __name__ == "__main__":
    generate_demand_data()