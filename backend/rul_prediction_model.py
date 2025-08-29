import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

class RULPredictor:
    def __init__(self):
        """
        Initializes the RUL (Remaining Useful Life) Predictor.
        Uses an XGBoost Regressor model.
        """
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        self.is_trained = False
        self.features = ['VibrationRMS', 'Temperature', 'RotationalSpeed', 'Cycle']

    def train(self, data_path="rul_data.csv"):
        """
        Trains the XGBoost model on the provided historical dataset.

        Args:
            data_path (str): The path to the CSV file containing training data.
        """
        print("Training RUL prediction model...")
        try:
            df = pd.read_csv(data_path)
        except FileNotFoundError:
            print(f"ERROR: RUL training data not found at '{data_path}'. Model will not be trained.")
            return

        X = df[self.features]
        y = df['RUL']

        # Split data for validation
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train the model
        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Evaluate the model
        preds = self.model.predict(X_test)
        rmse = mean_squared_error(y_test, preds, squared=False)
        print(f"RUL model training complete. Validation RMSE: {rmse:.2f} hours")

    def predict(self, latest_sensor_data):
        """
        Predicts the RUL based on the latest sensor readings.

        Args:
            latest_sensor_data (pd.DataFrame): A DataFrame containing one row
                                               of the latest sensor data.

        Returns:
            float: The predicted Remaining Useful Life in hours.
        """
        if not self.is_trained:
            raise RuntimeError("Model has not been trained yet. Cannot make predictions.")
        
        # Ensure the DataFrame has the correct feature columns
        data_for_prediction = latest_sensor_data[self.features]
        
        # Predict the RUL
        predicted_rul = self.model.predict(data_for_prediction)[0]
        
        # Ensure RUL is not negative
        return max(0, predicted_rul)