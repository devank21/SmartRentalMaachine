import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import numpy as np
import math
import traceback

# --- App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Data Loading and Preparation ---
try:
    df = pd.read_csv('rental_data.csv', na_values=['N/A', 'NaN', ''])
    df = df.replace({np.nan: None})
    df['RentalStartDate'] = pd.to_datetime(df['RentalStartDate'], errors='coerce')
    df['ExpectedReturnDate'] = pd.to_datetime(df['ExpectedReturnDate'], errors='coerce')
    print("CSV data loaded and cleaned successfully.")
except FileNotFoundError:
    print("FATAL: rental_data.csv not found. The app cannot run.")
    df = pd.DataFrame()

# --- Machine Learning Models ---
anomaly_model = None
availability_model = None
is_model_trained = False

if not df.empty:
    try:
        # Anomaly Detection Model
        anomaly_model = IsolationForest(contamination=0.05, random_state=42)
        telemetry_features = ['EngineHours', 'FuelLevel', 'EngineLoad']
        for col in telemetry_features:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col].fillna(df[col].median(), inplace=True)
        anomaly_model.fit(df[telemetry_features])
        df['IsAnomalous'] = anomaly_model.predict(df[telemetry_features])
        print("Anomaly detection model trained successfully.")

        # Predictive Availability Model
        availability_model = LinearRegression()
        if 'ActualReturnDate' in df.columns:
            df_train = df.dropna(subset=['ActualReturnDate', 'RentalStartDate', 'EngineHours']).copy()
            df_train['ActualReturnDate'] = pd.to_datetime(df_train['ActualReturnDate'], errors='coerce')
            if not df_train.empty:
                df_train['ActualDuration'] = (df_train['ActualReturnDate'] - df_train['RentalStartDate']).dt.days
                df_train = df_train[df_train['ActualDuration'] >= 0]
                if not df_train.empty and len(df_train) > 1:
                    X_train = df_train[['EngineHours']]
                    y_train = df_train['ActualDuration']
                    availability_model.fit(X_train, y_train)
                    is_model_trained = True
                    print("Predictive availability model trained successfully.")
                else:
                    print("Warning: Not enough valid historical data to train availability model.")
            else:
                print("Warning: No complete historical data for training availability model.")
        else:
            print("Warning: 'ActualReturnDate' column not found for training availability model.")
    except Exception as e:
        print(f"Error during model training: {e}")
        traceback.print_exc()

# --- Helper Functions ---
def haversine(lat1, lon1, lat2, lon2):
    if any(v is None for v in [lat1, lon1, lat2, lon2]): return None
    R = 6371
    dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def generate_alerts(vehicle):
    alerts = []
    dist = haversine(vehicle.get('Latitude'), vehicle.get('Longitude'), vehicle.get('JobSiteLat'), vehicle.get('JobSiteLon'))
    radius = vehicle.get('JobSiteRadius')
    if dist is not None and radius is not None and dist > radius:
        alerts.append({"type": "Geofence", "message": f"Vehicle is {dist:.2f} km from job site.", "level": "critical"})
    if vehicle.get('IsAnomalous') == -1:
        alerts.append({"type": "Telemetry", "message": "Anomalous sensor readings.", "level": "warning"})
    fuel_level = vehicle.get('FuelLevel')
    if fuel_level is not None and fuel_level < 15:
        alerts.append({"type": "Fuel", "message": f"Low fuel: {fuel_level}%", "level": "warning"})
    return alerts

# --- API Endpoints ---
@app.route('/api/summary', methods=['GET'])
def get_summary():
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        summary_df = df.groupby('Type')['Status'].value_counts().unstack(fill_value=0)
        summary_df['Total'] = summary_df.sum(axis=1)
        summary_list = [{'category': index, 'statuses': row.to_dict()} for index, row in summary_df.iterrows()]
        return jsonify({'data': summary_list})
    except Exception as e:
        return jsonify({"error": "Could not generate summary"}), 500

@app.route('/api/equipment/type/<type_name>', methods=['GET'])
def get_equipment_by_type(type_name):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        data = df[df['Type'] == type_name].copy()
        data['RentalStartDate'] = data['RentalStartDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        data['ExpectedReturnDate'] = data['ExpectedReturnDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        clean_data = data.to_dict(orient='records')
        return jsonify({'data': clean_data})
    except Exception as e:
        return jsonify({"error": f"Could not retrieve data for {type_name}"}), 500

@app.route('/api/equipment/id/<equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        vehicle_data = df[df['EquipmentID'] == equipment_id]
        if vehicle_data.empty: return jsonify({"error": "Vehicle not found"}), 404
        vehicle = vehicle_data.iloc[0].to_dict()
        vehicle['alerts'] = generate_alerts(vehicle)
        if pd.notna(vehicle.get('RentalStartDate')):
            vehicle['RentalStartDate'] = vehicle['RentalStartDate'].strftime('%Y-%m-%d')
        if pd.notna(vehicle.get('ExpectedReturnDate')):
            vehicle['ExpectedReturnDate'] = vehicle['ExpectedReturnDate'].strftime('%Y-%m-%d')
        return jsonify(vehicle)
    except Exception as e:
        return jsonify({"error": "Could not retrieve vehicle details"}), 500

@app.route('/api/predict-availability', methods=['POST'])
def predict_availability():
    if not is_model_trained:
        return jsonify({"error": "Prediction model not available: not enough historical data."}), 503
    try:
        data = request.json
        equipment_id = data.get('equipmentId')
        future_date_str = data.get('futureDate')
        if not equipment_id or not future_date_str:
            return jsonify({"error": "Missing equipment ID or future date."}), 400
        vehicle_series = df[df['EquipmentID'] == equipment_id].iloc[0]
        future_date = datetime.strptime(future_date_str, '%Y-%m-%d')
        if vehicle_series['Status'] == 'Available':
            return jsonify({"available": True, "predictedReturnDate": "Now"})
        if pd.isna(vehicle_series['RentalStartDate']):
            return jsonify({"error": "Cannot predict: Vehicle has no rental start date."}), 422
        engine_hours = vehicle_series[['EngineHours']]
        duration_days = availability_model.predict(engine_hours)[0]
        predicted_return_date = vehicle_series['RentalStartDate'] + timedelta(days=int(duration_days))
        return jsonify({
            "available": future_date > predicted_return_date,
            "predictedReturnDate": predicted_return_date.strftime('%Y-%m-%d')
        })
    except IndexError:
        return jsonify({"error": f"Equipment ID '{equipment_id}' not found."}), 404
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred during prediction."}), 500

@app.route('/api/sustainability/report', methods=['GET'])
def get_sustainability_report():
    if df.empty:
        return jsonify({"error": "Dataset not loaded"}), 500
    try:
        report = {}
        EMISSION_FACTORS = {'low_load': 10, 'medium_load': 20, 'high_load': 30}
        
        # DEFINITIVE FIX: Use a safer calculation method
        def calculate_emissions(row):
            engine_hours = row['EngineHours']
            engine_load = row['EngineLoad']
            if pd.isna(engine_hours) or pd.isna(engine_load):
                return 0
            if engine_load < 20: return engine_hours * EMISSION_FACTORS['low_load']
            if engine_load < 70: return engine_hours * EMISSION_FACTORS['medium_load']
            return engine_hours * EMISSION_FACTORS['high_load']

        df['Emissions'] = df.apply(calculate_emissions, axis=1)
        
        # Group by type and perform safe aggregations
        report_df = df.groupby('Type').agg(
            total_emissions_kg_co2e=('Emissions', 'sum'),
            total_engine_hours=('EngineHours', 'sum'),
            average_fuel_level=('FuelLevel', 'mean')
        ).reset_index()

        # Fill any potential NaN results from aggregation with 0
        report_df.fillna(0, inplace=True)
        
        # Convert the clean DataFrame to the desired dictionary format
        for _, row in report_df.iterrows():
            report[row['Type']] = {
                'total_emissions_kg_co2e': round(row['total_emissions_kg_co2e'], 2),
                'total_engine_hours': round(row['total_engine_hours'], 2),
                'average_fuel_level': round(row['average_fuel_level'], 2)
            }
            
        return jsonify({'data': report})
    except Exception as e:
        print(f"ERROR in get_sustainability_report: {e}")
        traceback.print_exc()
        return jsonify({"error": "Could not generate sustainability report"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True)