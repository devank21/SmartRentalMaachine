import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import warnings

warnings.filterwarnings("ignore")

class HybridProphetLSTM:
    def __init__(self, data_path='demand_data.csv'):
        self.df = pd.read_csv(data_path)
        self.df['ds'] = pd.to_datetime(self.df['ds'])
        self.prophet_model = None
        self.lstm_model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def _create_lstm_dataset(self, data, n_steps=30):
        X, y = [], []
        for i in range(len(data) - n_steps):
            X.append(data[i:(i + n_steps), 0])
            y.append(data[i + n_steps, 0])
        return np.array(X), np.array(y)

    def train(self):
        # Step 1: Trend and Seasonality Modeling with Prophet
        print("Training Prophet model...")
        self.prophet_model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0
        )
        self.prophet_model.fit(self.df)
        print("Prophet model trained.")

        # Step 2: Residual Calculation
        forecast = self.prophet_model.predict(self.df[['ds']])
        residuals = self.df['y'].values - forecast['yhat'].values
        
        # Step 3: Non-Linear Pattern Learning with LSTM
        print("Training LSTM model on residuals...")
        scaled_residuals = self.scaler.fit_transform(residuals.reshape(-1, 1))
        
        n_steps = 60 # Look back at the last 60 days of residuals to predict the next
        X, y = self._create_lstm_dataset(scaled_residuals, n_steps)
        X = X.reshape((X.shape[0], X.shape[1], 1))

        self.lstm_model = Sequential()
        self.lstm_model.add(LSTM(50, activation='relu', input_shape=(n_steps, 1)))
        self.lstm_model.add(Dense(1))
        self.lstm_model.compile(optimizer='adam', loss='mse')
        
        self.lstm_model.fit(X, y, epochs=50, verbose=0)
        print("LSTM model trained.")

    def predict(self, periods=365):
        if not self.prophet_model or not self.lstm_model:
            raise Exception("Models are not trained. Please call train() first.")

        # Step 4.1: Prophet Forecast
        future_dates = self.prophet_model.make_future_dataframe(periods=periods)
        prophet_forecast = self.prophet_model.predict(future_dates)

        # Step 4.2: LSTM Residual Forecast
        # Get historical residuals for prediction input
        forecast_history = self.prophet_model.predict(self.df[['ds']])
        residuals_history = self.df['y'].values - forecast_history['yhat'].values
        scaled_residuals_history = self.scaler.transform(residuals_history.reshape(-1, 1))

        # Predict future residuals step-by-step
        n_steps = 60
        input_seq = scaled_residuals_history[-n_steps:].flatten().tolist()
        predicted_residuals_scaled = []

        for _ in range(periods):
            input_array = np.array(input_seq[-n_steps:]).reshape(1, n_steps, 1)
            prediction = self.lstm_model.predict(input_array, verbose=0)[0,0]
            predicted_residuals_scaled.append(prediction)
            input_seq.append(prediction)

        predicted_residuals = self.scaler.inverse_transform(np.array(predicted_residuals_scaled).reshape(-1, 1)).flatten()

        # Step 4.3: Combine Forecasts
        final_forecast = prophet_forecast.copy()
        
        # Add LSTM predictions to the future part of the forecast
        final_forecast.loc[len(self.df):, 'yhat'] = final_forecast.loc[len(self.df):, 'yhat'] + predicted_residuals
        
        # Combine historical data with forecast for plotting
        result = self.df.copy()
        result = result.rename(columns={'y': 'actual'})
        
        final_forecast_plot = final_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
        result = pd.merge(result, final_forecast_plot, on='ds', how='right')
        
        return result

# Example usage:
if __name__ == '__main__':
    model = HybridProphetLSTM()
    model.train()
    forecast_df = model.predict(periods=90)
    print("Forecast generated successfully.")
    print(forecast_df.tail())