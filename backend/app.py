import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import numpy as np
import math
import traceback
import os

# --- Custom Model Imports ---
from demand_forecasting_model import HybridProphetLSTM
from behavioral_anomaly_model import LSTMAutoencoder

# --- App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Data Loading and Preparation ---
# Check for necessary data files on startup
if not os.path.exists('demand_data.csv'):
    print("FATAL: demand_data.csv not found. Please run generate_demand_data.py first.")
if not os.path.exists('operational_data.csv'):
    print("FATAL: operational_data.csv not found. Please run generate_operational_data.py first.")

try:
    df = pd.read_csv('rental_data.csv', na_values=['N/A', 'NaN', ''])
    df = df.replace({np.nan: None})
    df['RentalStartDate'] = pd.to_datetime(df['RentalStartDate'], errors='coerce')
    df['ExpectedReturnDate'] = pd.to_datetime(df['ExpectedReturnDate'], errors='coerce')
    print("Rental data loaded and cleaned successfully.")
except FileNotFoundError:
    print("FATAL: rental_data.csv not found. The app cannot run.")
    df = pd.DataFrame()

# --- Machine Learning Models Initialization ---
anomaly_model = None
availability_model = None
pricing_model = None
is_availability_model_trained = False
is_pricing_model_trained = False
anomaly_detector = None
operational_df = None
SEQUENCE_LENGTH = 30 # Must match the behavioral model's sequence length

# --- Train Core Models ---
if not df.empty:
    try:
        # 1. Telemetry Anomaly Detection Model (Isolation Forest)
        anomaly_model = IsolationForest(contamination=0.05, random_state=42)
        telemetry_features = ['EngineHours', 'FuelLevel', 'EngineLoad']
        for col in telemetry_features:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col].fillna(df[col].median(), inplace=True)
        anomaly_model.fit(df[telemetry_features])
        df['IsAnomalous'] = anomaly_model.predict(df[telemetry_features])
        print("Telemetry anomaly detection model (Isolation Forest) trained successfully.")

        # 2. Predictive Availability Model (Linear Regression)
        availability_model = LinearRegression()
        if 'ActualReturnDate' in df.columns:
            df_train_avail = df.dropna(subset=['ActualReturnDate', 'RentalStartDate', 'EngineHours']).copy()
            if not df_train_avail.empty:
                df_train_avail['ActualDuration'] = (pd.to_datetime(df_train_avail['ActualReturnDate']) - df_train_avail['RentalStartDate']).dt.days
                df_train_avail = df_train_avail[df_train_avail['ActualDuration'] >= 0]
                if not df_train_avail.empty and len(df_train_avail) > 1:
                    X_train_avail, y_train_avail = df_train_avail[['EngineHours']], df_train_avail['ActualDuration']
                    availability_model.fit(X_train_avail, y_train_avail)
                    is_availability_model_trained = True
                    print("Predictive availability model trained successfully.")

        # 3. Dynamic Pricing Model (Linear Regression)
        pricing_model = LinearRegression()
        if 'RentalPrice' in df.columns:
            df_train_price = df.dropna(subset=['RentalPrice', 'EngineHours']).copy()
            if not df_train_price.empty and len(df_train_price) > 1:
                X_train_price, y_train_price = df_train_price[['EngineHours']], df_train_price['RentalPrice']
                pricing_model.fit(X_train_price, y_train_price)
                is_pricing_model_trained = True
                print("Dynamic pricing model trained successfully.")

    except Exception as e:
        print(f"Error during core model training: {e}")

# --- Train Behavioral Anomaly Detection Model (LSTM Autoencoder) ---
try:
    operational_df = pd.read_csv('operational_data.csv')
    operational_df['Timestamp'] = pd.to_datetime(operational_df['Timestamp'])
    
    # --- FIX HERE: Use an EquipmentID that exists in your data ---
    # Train the model only on data known to be "normal"
    normal_training_data = operational_df[operational_df['EquipmentID'] == 'CAT-D5']
    
    if not normal_training_data.empty:
        anomaly_detector = LSTMAutoencoder(sequence_length=SEQUENCE_LENGTH)
        anomaly_detector.train(normal_training_data)
        print("Behavioral anomaly detection model (LSTM Autoencoder) trained successfully.")
    else:
        print("Could not find normal operational data to train behavioral anomaly detector.")

except FileNotFoundError:
    print("WARNING: operational_data.csv not found. Behavioral anomaly detection will be disabled.")
except Exception as e:
    print(f"Error initializing behavioral anomaly detection model: {e}")
    traceback.print_exc()


# --- Helper Functions ---
def haversine(lat1, lon1, lat2, lon2):
    if any(v is None or not isinstance(v, (int, float)) for v in [lat1, lon1, lat2, lon2]):
        return None
    R = 6371
    dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def generate_alerts(vehicle):
    alerts = []
    try:
        dist = haversine(vehicle.get('Latitude'), vehicle.get('Longitude'), vehicle.get('JobSiteLat'), vehicle.get('JobSiteLon'))
        radius = vehicle.get('JobSiteRadius')
        if dist is not None and radius is not None and isinstance(radius, (int, float)) and dist > radius:
            alerts.append({"type": "Geofence", "message": f"Vehicle is {dist:.2f} km from job site.", "level": "critical"})

        if vehicle.get('IsAnomalous') == -1:
            alerts.append({"type": "Telemetry", "message": "Anomalous sensor readings detected.", "level": "warning"})

        fuel = vehicle.get('FuelLevel')
        if fuel is not None and isinstance(fuel, (int, float)) and fuel < 15:
            alerts.append({"type": "Fuel", "message": f"Low fuel: {fuel}%", "level": "warning"})
    except Exception as e:
        print(f"Alert generation failed: {e}")
    return alerts

# --- API Endpoints (omitted for brevity, no changes here) ---
# ... All your existing @app.route endpoints go here ...
@app.route('/api/summary', methods=['GET'])
def get_summary():
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        summary_df = df.groupby('Type')['Status'].value_counts().unstack(fill_value=0)
        summary_df['Total'] = summary_df.sum(axis=1)
        return jsonify({'data': [{'category': index, 'statuses': row.to_dict()} for index, row in summary_df.iterrows()]})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Could not generate summary"}), 500

@app.route('/api/equipment/type/<type_name>', methods=['GET'])
def get_equipment_by_type(type_name):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        data = df[df['Type'] == type_name].copy()
        data['RentalStartDate'] = data['RentalStartDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        data['ExpectedReturnDate'] = data['ExpectedReturnDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        return jsonify({'data': data.to_dict(orient='records')})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Could not retrieve data for {type_name}"}), 500

@app.route('/api/equipment/id/<equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        vehicle_data = df[df['EquipmentID'] == equipment_id]
        if vehicle_data.empty: return jsonify({"error": "Vehicle not found"}), 404
        vehicle = vehicle_data.iloc[0].to_dict()
        vehicle['alerts'] = generate_alerts(vehicle)
        if pd.notna(vehicle.get('RentalStartDate')): vehicle['RentalStartDate'] = vehicle['RentalStartDate'].strftime('%Y-%m-%d')
        if pd.notna(vehicle.get('ExpectedReturnDate')): vehicle['ExpectedReturnDate'] = vehicle['ExpectedReturnDate'].strftime('%Y-%m-%d')
        return jsonify(vehicle)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Could not retrieve vehicle details"}), 500

@app.route('/api/predict-availability', methods=['POST'])
def predict_availability():
    try:
        data = request.json
        date_str = data['futureDate'].strip()
        future_date = None
        for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                future_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        if future_date is None:
            return jsonify({"error": f"Invalid date format. Got '{date_str}', expected DD-MM-YYYY"}), 400

        vehicle_data = df[df['EquipmentID'] == data['equipmentId']]
        if vehicle_data.empty: return jsonify({"error": "Equipment not found"}), 404
        vehicle = vehicle_data.iloc[0]

        if vehicle['Status'] == 'Available':
            return jsonify({"available": True, "predictedReturnDate": "Now"})

        if pd.isna(vehicle['RentalStartDate']):
            return jsonify({"error": "No rental start date."}), 422

        predicted_return = None
        if is_availability_model_trained and not pd.isna(vehicle['EngineHours']):
            try:
                duration = availability_model.predict([[vehicle['EngineHours']]])[0]
                predicted_return = vehicle['RentalStartDate'] + timedelta(days=int(duration))
            except Exception as e:
                print("Model prediction error:", e)

        if predicted_return is None:
            if not pd.isna(vehicle['ExpectedReturnDate']):
                predicted_return = vehicle['ExpectedReturnDate']
            else:
                avg_duration = (df['ExpectedReturnDate'] - df['RentalStartDate']).dt.days.mean()
                predicted_return = vehicle['RentalStartDate'] + timedelta(days=int(avg_duration))

        available = future_date > predicted_return
        return jsonify({"available": bool(available), "predictedReturnDate": predicted_return.strftime('%Y-%m-%d')})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error during availability prediction: {str(e)}"}), 500

@app.route('/api/sustainability/report', methods=['GET'])
def get_sustainability_report():
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        def calc_emissions(row):
            if pd.isna(row['EngineHours']) or pd.isna(row['EngineLoad']): return 0
            if row['EngineLoad'] < 20: return row['EngineHours'] * 10
            if row['EngineLoad'] < 70: return row['EngineHours'] * 20
            return row['EngineHours'] * 30
        df['Emissions'] = df.apply(calc_emissions, axis=1)
        report_df = df.groupby('Type').agg(total_emissions_kg_co2e=('Emissions', 'sum'), total_engine_hours=('EngineHours', 'sum'), average_fuel_level=('FuelLevel', 'mean')).reset_index().fillna(0)
        report = {row['Type']: {k: round(v, 2) for k, v in row.to_dict().items() if k != 'Type'} for _, row in report_df.iterrows()}
        return jsonify({'data': report})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Could not generate sustainability report"}), 500

@app.route('/api/return-vehicle', methods=['POST'])
def return_vehicle():
    global df
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        equipment_id = request.json.get('equipmentId')
        idx = df.index[df['EquipmentID'] == equipment_id]
        if idx.empty: return jsonify({"error": "Vehicle not found"}), 404
        df.loc[idx, 'Status'] = 'Available'
        df.loc[idx, 'ActualReturnDate'] = datetime.now().strftime('%Y-%m-%d')
        df.loc[idx, ['Customer', 'JobSiteName']] = None
        updated_vehicle = df.loc[idx[0]].to_dict()
        return jsonify(updated_vehicle)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error processing return: {e}"}), 500

@app.route('/api/predict-price', methods=['POST'])
def predict_price():
    if not is_pricing_model_trained: return jsonify({"error": "Pricing model not available."}), 503
    try:
        data = request.json
        engine_hours, duration_days = data.get('engineHours'), data.get('durationDays')
        if engine_hours is None or duration_days is None: return jsonify({"error": "Missing engine hours or duration."}), 400
        base_price = pricing_model.predict(np.array([[engine_hours]]))[0]
        final_price = base_price * (1 + (int(duration_days) / 100))
        return jsonify({"predictedPrice": round(final_price, 2)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error predicting price: {e}"}), 500

@app.route('/api/predict-demand', methods=['POST'])
def predict_demand():
    try:
        model = HybridProphetLSTM(data_path='demand_data.csv')
        model.train()
        forecast_df = model.predict(periods=90)
        forecast_df = forecast_df.replace({np.nan: None})
        forecast_df['ds'] = forecast_df['ds'].dt.strftime('%Y-%m-%d')
        return jsonify(forecast_df.to_dict(orient='records'))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error during demand prediction: {str(e)}"}), 500

@app.route('/api/analyze-behavior/<equipment_id>', methods=['POST'])
def analyze_behavior(equipment_id):
    if anomaly_detector is None or operational_df is None:
        return jsonify({"error": "Anomaly detection service is not available."}), 503

    try:
        vehicle_data = operational_df[operational_df['EquipmentID'] == equipment_id].copy()
        vehicle_data.sort_values(by='Timestamp', inplace=True)
        
        if len(vehicle_data) < SEQUENCE_LENGTH:
            return jsonify({"error": f"Not enough historical data. Need {SEQUENCE_LENGTH} records, found {len(vehicle_data)}."}), 400
            
        latest_sequence_df = vehicle_data.tail(SEQUENCE_LENGTH)
        reconstruction_error = anomaly_detector.predict(latest_sequence_df)
        threshold = anomaly_detector.training_mae_loss * 2.5
        is_anomaly = reconstruction_error > threshold

        sequence_for_chart = latest_sequence_df[['Timestamp', 'EngineLoad']].to_dict(orient='records')
        for record in sequence_for_chart:
            record['Timestamp'] = record['Timestamp'].strftime('%H:%M:%S')

        return jsonify({
            "is_anomaly": bool(is_anomaly),
            "reconstruction_error": float(reconstruction_error),
            "threshold": float(threshold),
            "sequence_data": sequence_for_chart
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error during behavioral analysis: {str(e)}"}), 500
# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True)