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
if not os.path.exists('demand_data.csv'):
    print("FATAL: demand_data.csv not found.")
if not os.path.exists('operational_data.csv'):
    print("FATAL: operational_data.csv not found.")

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
demand_model = None # For demand forecasting
SEQUENCE_LENGTH = 30

# --- Train All Models on Startup ---
try:
    # 1. Telemetry Anomaly Detection
    if not df.empty:
        anomaly_model = IsolationForest(contamination=0.05, random_state=42)
        telemetry_features = ['EngineHours', 'FuelLevel', 'EngineLoad']
        for col in telemetry_features:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col].fillna(df[col].median(), inplace=True)
        anomaly_model.fit(df[telemetry_features])
        df['IsAnomalous'] = anomaly_model.predict(df[telemetry_features])
        print("Telemetry anomaly detection model trained.")

    # 2. Predictive Availability
    if not df.empty and 'ActualReturnDate' in df.columns:
        availability_model = LinearRegression()
        df_train_avail = df.dropna(subset=['ActualReturnDate', 'RentalStartDate', 'EngineHours']).copy()
        df_train_avail['ActualDuration'] = (pd.to_datetime(df_train_avail['ActualReturnDate']) - df_train_avail['RentalStartDate']).dt.days
        df_train_avail = df_train_avail[df_train_avail['ActualDuration'] >= 0]
        if len(df_train_avail) > 1:
            availability_model.fit(df_train_avail[['EngineHours']], df_train_avail['ActualDuration'])
            is_availability_model_trained = True
            print("Predictive availability model trained.")

    # 3. Dynamic Pricing
    if not df.empty and 'RentalPrice' in df.columns:
        pricing_model = LinearRegression()
        df_train_price = df.dropna(subset=['RentalPrice', 'EngineHours']).copy()
        if len(df_train_price) > 1:
            pricing_model.fit(df_train_price[['EngineHours']], df_train_price['RentalPrice'])
            is_pricing_model_trained = True
            print("Dynamic pricing model trained.")
            
    # 4. Behavioral Anomaly Detection
    operational_df = pd.read_csv('operational_data.csv')
    operational_df['Timestamp'] = pd.to_datetime(operational_df['Timestamp'])
    normal_training_data = operational_df[operational_df['EquipmentID'] == 'CAT-D5'] # Using a known normal vehicle
    if not normal_training_data.empty:
        anomaly_detector = LSTMAutoencoder(sequence_length=SEQUENCE_LENGTH)
        anomaly_detector.train(normal_training_data)
        print("Behavioral anomaly detection model trained.")

    # 5. Demand Forecasting
    demand_model = HybridProphetLSTM(data_path='demand_data.csv')
    demand_model.train()
    print("Demand forecasting model trained.")

except Exception as e:
    print(f"A critical error occurred during model training: {e}")
    traceback.print_exc()


# --- Helper Functions (unchanged) ---
def haversine(lat1, lon1, lat2, lon2):
    if any(v is None or not isinstance(v, (int, float)) for v in [lat1, lon1, lat2, lon2]): return None
    R = 6371
    dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def generate_alerts(vehicle):
    alerts = []
    dist = haversine(vehicle.get('Latitude'), vehicle.get('Longitude'), vehicle.get('JobSiteLat'), vehicle.get('JobSiteLon'))
    radius = vehicle.get('JobSiteRadius')
    if dist is not None and radius is not None and isinstance(radius, (int, float)) and dist > radius:
        alerts.append({"type": "Geofence", "message": f"Vehicle is {dist:.2f} km from job site.", "level": "critical"})
    if vehicle.get('IsAnomalous') == -1:
        alerts.append({"type": "Telemetry", "message": "Anomalous sensor readings.", "level": "warning"})
    fuel = vehicle.get('FuelLevel')
    if fuel is not None and isinstance(fuel, (int, float)) and fuel < 15:
        alerts.append({"type": "Fuel", "message": f"Low fuel: {fuel}%", "level": "warning"})
    return alerts

# --- API Endpoints ---
@app.route('/api/summary', methods=['GET'])
def get_summary():
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    summary_df = df.groupby('Type')['Status'].value_counts().unstack(fill_value=0)
    summary_df['Total'] = summary_df.sum(axis=1)
    return jsonify({'data': [{'category': index, 'statuses': row.to_dict()} for index, row in summary_df.iterrows()]})

@app.route('/api/equipment/type/<type_name>', methods=['GET'])
def get_equipment_by_type(type_name):
    data = df[df['Type'] == type_name].copy()
    data['RentalStartDate'] = data['RentalStartDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
    data['ExpectedReturnDate'] = data['ExpectedReturnDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
    return jsonify({'data': data.to_dict(orient='records')})

@app.route('/api/equipment/id/<equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    vehicle_data = df[df['EquipmentID'] == equipment_id]
    if vehicle_data.empty: return jsonify({"error": "Vehicle not found"}), 404
    vehicle = vehicle_data.iloc[0].to_dict()
    vehicle['alerts'] = generate_alerts(vehicle)
    if pd.notna(vehicle.get('RentalStartDate')): vehicle['RentalStartDate'] = vehicle['RentalStartDate'].strftime('%Y-%m-%d')
    if pd.notna(vehicle.get('ExpectedReturnDate')): vehicle['ExpectedReturnDate'] = vehicle['ExpectedReturnDate'].strftime('%Y-%m-%d')
    return jsonify(vehicle)

@app.route('/api/predict-demand', methods=['GET']) # Changed to GET
def predict_demand():
    if demand_model is None:
        return jsonify({"error": "Demand forecasting model is not available."}), 503
    try:
        forecast_df = demand_model.predict(periods=90)
        forecast_df = forecast_df.replace({np.nan: None})
        forecast_df['ds'] = forecast_df['ds'].dt.strftime('%Y-%m-%d')
        return jsonify(forecast_df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": f"Error during demand prediction: {str(e)}"}), 500

@app.route('/api/analyze-behavior/<equipment_id>', methods=['GET']) # Changed to GET
def analyze_behavior(equipment_id):
    if anomaly_detector is None: return jsonify({"error": "Behavioral anomaly service is not available."}), 503
    try:
        vehicle_data = operational_df[operational_df['EquipmentID'] == equipment_id].copy()
        if len(vehicle_data) < SEQUENCE_LENGTH:
            return jsonify({"error": f"Not enough data. Need {SEQUENCE_LENGTH} records, found {len(vehicle_data)}."}), 400
        latest_sequence = vehicle_data.tail(SEQUENCE_LENGTH)
        error = anomaly_detector.predict(latest_sequence)
        threshold = anomaly_detector.training_mae_loss * 2.5 # 2.5x the training error
        is_anomaly = error > threshold
        chart_data = latest_sequence[['Timestamp', 'EngineLoad']].to_dict(orient='records')
        for record in chart_data: record['Timestamp'] = record['Timestamp'].strftime('%H:%M:%S')
        return jsonify({
            "is_anomaly": bool(is_anomaly),
            "reconstruction_error": float(error),
            "threshold": float(threshold),
            "sequence_data": chart_data
        })
    except Exception as e:
        return jsonify({"error": f"Error during analysis: {str(e)}"}), 500
        
# Other endpoints (unchanged)
@app.route('/api/predict-availability', methods=['POST'])
def predict_availability():
    if not is_availability_model_trained: return jsonify({"error": "Availability model not trained."}), 503
    data = request.json
    vehicle = df[df['EquipmentID'] == data['equipmentId']].iloc[0]
    if vehicle['Status'] == 'Available': return jsonify({"available": True, "predictedReturnDate": "Now"})
    if pd.isna(vehicle['RentalStartDate']): return jsonify({"error": "No rental start date."}), 422
    duration = availability_model.predict(vehicle[['EngineHours']])[0]
    predicted_return = vehicle['RentalStartDate'] + timedelta(days=int(duration))
    return jsonify({"available": datetime.strptime(data['futureDate'], '%Y-%m-%d') > predicted_return, "predictedReturnDate": predicted_return.strftime('%Y-%m-%d')})

@app.route('/api/predict-price', methods=['POST'])
def predict_price():
    if not is_pricing_model_trained: return jsonify({"error": "Pricing model not available."}), 503
    data = request.json
    engine_hours, duration_days = data.get('engineHours'), data.get('durationDays')
    base_price = pricing_model.predict(np.array([[engine_hours]]))[0]
    final_price = base_price * (1 + (int(duration_days) / 100))
    return jsonify({"predictedPrice": round(final_price, 2)})

@app.route('/api/sustainability/report', methods=['GET'])
def get_sustainability_report():
    def calc_emissions(row):
        if pd.isna(row['EngineHours']) or pd.isna(row['EngineLoad']): return 0
        if row['EngineLoad'] < 20: return row['EngineHours'] * 10
        if row['EngineLoad'] < 70: return row['EngineHours'] * 20
        return row['EngineHours'] * 30
    df['Emissions'] = df.apply(calc_emissions, axis=1)
    report_df = df.groupby('Type').agg(total_emissions_kg_co2e=('Emissions', 'sum'), total_engine_hours=('EngineHours', 'sum'), average_fuel_level=('FuelLevel', 'mean')).reset_index().fillna(0)
    report = {row['Type']: {k: round(v, 2) for k, v in row.to_dict().items() if k != 'Type'} for _, row in report_df.iterrows()}
    return jsonify({'data': report})

@app.route('/api/return-vehicle', methods=['POST'])
def return_vehicle():
    global df
    equipment_id = request.json.get('equipmentId')
    idx = df.index[df['EquipmentID'] == equipment_id]
    if idx.empty: return jsonify({"error": "Vehicle not found"}), 404
    df.loc[idx, 'Status'] = 'Available'
    df.loc[idx, 'ActualReturnDate'] = datetime.now().strftime('%Y-%m-%d')
    df.loc[idx, ['Customer', 'JobSiteName']] = None
    return jsonify(df.loc[idx[0]].to_dict())

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False) # Important: disable reloader to prevent re-training