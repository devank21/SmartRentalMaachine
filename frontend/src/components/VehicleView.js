import React, { useEffect, useState } from "react";
import axios from "axios";
import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import "./VehicleView.css";

// --- Leaflet Icon Fix ---
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require("leaflet/dist/images/marker-icon-2x.png"),
  iconUrl: require("leaflet/dist/images/marker-icon.png"),
  shadowUrl: require("leaflet/dist/images/marker-shadow.png"),
});

const API_BASE_URL = "http://127.0.0.1:5000/api";

const VehicleView = ({ equipmentId, category, navigateTo }) => {
  const [vehicle, setVehicle] = useState(null);
  const [error, setError] = useState("");
  const [prediction, setPrediction] = useState(null);
  const [date, setDate] = useState("");

  // State for new features
  const [pricePrediction, setPricePrediction] = useState(null);
  const [duration, setDuration] = useState(90); // Default duration
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const fetchVehicleData = () => {
    axios
      .get(`${API_BASE_URL}/equipment/id/${equipmentId}`)
      .then((res) => setVehicle(res.data))
      .catch((err) => {
        console.error(`Error fetching vehicle ${equipmentId}:`, err);
        setError("Could not load vehicle details.");
      });
  };

  useEffect(() => {
    fetchVehicleData();
  }, [equipmentId]);

  const handleAvailabilityPrediction = () => {
    if (!date) return;
    setPrediction(null);
    axios
      .post(`${API_BASE_URL}/predict-availability`, {
        equipmentId,
        futureDate: date,
      })
      .then((res) => setPrediction(res.data))
      .catch((err) =>
        setPrediction({
          error: err.response?.data?.error || "Could not get prediction.",
        })
      );
  };

  const handlePricePrediction = () => {
    setPricePrediction(null);
    axios
      .post(`${API_BASE_URL}/predict-price`, {
        engineHours: vehicle.EngineHours,
        durationDays: duration,
      })
      .then((res) => setPricePrediction(res.data))
      .catch((err) =>
        setPricePrediction({
          error: err.response?.data?.error || "Could not get price.",
        })
      );
  };

  const handleReturnVehicle = () => {
    axios
      .post(`${API_BASE_URL}/return-vehicle`, { equipmentId })
      .then((res) => {
        fetchVehicleData(); // Refresh data to show "Available" status
      })
      .catch((err) => console.error("Error returning vehicle:", err));
  };

  const handleAnalyzeBehavior = async () => {
    setIsAnalyzing(true);
    setAnalysisResult(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/analyze-behavior/${equipmentId}`,
        {
          method: "POST",
        }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to analyze behavior.");
      }
      setAnalysisResult(data);
    } catch (error) {
      console.error("Analysis Error:", error);
      setAnalysisResult({ error: error.message });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const renderPredictionResult = (pred) => {
    if (!pred) return null;
    if (pred.error)
      return <div className="prediction-result error">{pred.error}</div>;
    if (pred.available)
      return (
        <div className="prediction-result available">
          Predicted to be AVAILABLE on {date}.
        </div>
      );
    return (
      <div className="prediction-result in-use">
        Predicted to be IN-USE. Expected return: {pred.predictedReturnDate}.
      </div>
    );
  };

  const renderPriceResult = (price) => {
    if (!price) return null;
    if (price.error)
      return <div className="prediction-result error">{price.error}</div>;
    return (
      <div className="prediction-result success">
        Estimated Price: ${price.predictedPrice.toLocaleString()}
      </div>
    );
  };

  if (error) return <div className="error-message">{error}</div>;
  if (!vehicle) return <div className="loading">Loading vehicle data...</div>;

  return (
    <div className="view-container">
      <button
        className="back-button"
        onClick={() => navigateTo("category", { category: vehicle.Type })}
      >
        &larr; Back to {vehicle.Type}
      </button>
      <div className="vehicle-header">
        <h2>Vehicle Details: {vehicle.EquipmentID}</h2>
        {vehicle.Status === "In-Use" && (
          <button className="return-button" onClick={handleReturnVehicle}>
            Mark as Returned
          </button>
        )}
      </div>

      <div className="vehicle-grid">
        <div className="vehicle-card map-card">
          <h3>Live Location & Geofence</h3>
          <MapContainer
            center={[vehicle.Latitude, vehicle.Longitude]}
            zoom={14}
            style={{ height: "50%", width: "50%" }}
          >
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <Marker position={[vehicle.Latitude, vehicle.Longitude]}>
              <Popup>{vehicle.EquipmentID}</Popup>
            </Marker>
            {vehicle.JobSiteLat && vehicle.JobSiteLon && (
              <Circle
                center={[vehicle.JobSiteLat, vehicle.JobSiteLon]}
                radius={vehicle.JobSiteRadius * 1000} // Convert km to meters
                pathOptions={{ color: "green", fillColor: "green" }}
              />
            )}
          </MapContainer>
        </div>
        <div className="vehicle-card telemetry-card">
          <h3>Live Telemetry</h3>
          <div className="telemetry-item">
            <span>Status</span>
            <strong>{vehicle.Status}</strong>
          </div>
          <div className="telemetry-item">
            <span>Customer</span>
            <strong>{vehicle.Customer || "N/A"}</strong>
          </div>
          <div className="telemetry-item">
            <span>Fuel Level</span>
            <div className="progress-bar">
              <div style={{ width: `${vehicle.FuelLevel}%` }}>
                {vehicle.FuelLevel}%
              </div>
            </div>
          </div>
          <div className="telemetry-item">
            <span>Engine Hours</span>
            <strong>{vehicle.EngineHours} hrs</strong>
          </div>
          <div className="telemetry-item">
            <span>Engine Load</span>
            <div className="progress-bar">
              <div style={{ width: `${vehicle.EngineLoad}%` }}>
                {vehicle.EngineLoad}%
              </div>
            </div>
          </div>
        </div>
        <div className="vehicle-card alerts-card">
          <h3>System Alerts</h3>
          {vehicle.alerts?.length > 0 ? (
            <ul>
              {vehicle.alerts.map((alert, i) => (
                <li key={i} className={`alert-${alert.level}`}>
                  <strong>{alert.type}:</strong> {alert.message}
                </li>
              ))}
            </ul>
          ) : (
            <p>No active alerts.</p>
          )}
        </div>
        <div className="vehicle-card prediction-card">
          <h3>Predict Availability</h3>
          <p>Check if this machine will be free for a future date.</p>
          <div className="prediction-controls">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
            <button onClick={handleAvailabilityPrediction}>Check</button>
          </div>
          {renderPredictionResult(prediction)}
        </div>
        <div className="vehicle-card prediction-card">
          <h3>Dynamic Price Estimation</h3>
          <p>Estimate the rental price based on usage and duration.</p>
          <div className="prediction-controls">
            <label>Rental Duration (days):</label>
            <input
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
            <button onClick={handlePricePrediction}>Predict Price</button>
          </div>
          {renderPriceResult(pricePrediction)}
        </div>

        {/* --- New Behavioral Analysis Section --- */}
        <div className="vehicle-card behavioral-analysis">
          <h3>Behavioral Anomaly Detection</h3>
          <p>
            Analyze the machine's recent operational pattern to detect
            inefficient use, such as prolonged idling under no load.
          </p>
          <button onClick={handleAnalyzeBehavior} disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing..." : "Analyze Recent Behavior"}
          </button>

          {analysisResult && (
            <div className="analysis-result">
              <h4>Analysis Complete</h4>
              {analysisResult.error ? (
                <div className="result-summary error">
                  {analysisResult.error}
                </div>
              ) : (
                <>
                  <div
                    className={`result-summary ${
                      analysisResult.is_anomaly ? "anomaly" : "normal"
                    }`}
                  >
                    <strong>Status:</strong>{" "}
                    {analysisResult.is_anomaly
                      ? "Anomaly Detected (Under-Utilization)"
                      : "Normal Operation"}
                  </div>
                  <p>
                    <strong>Reconstruction Error:</strong>{" "}
                    {analysisResult.reconstruction_error.toFixed(4)}
                    <br />
                    <em>
                      (Anomaly Threshold: &gt;
                      {analysisResult.threshold.toFixed(4)})
                    </em>
                  </p>
                  <p>
                    {analysisResult.is_anomaly
                      ? "The machine's recent activity pattern is unusual and suggests it may be running without performing productive work."
                      : "The machine's recent activity aligns with patterns of normal, productive operation."}
                  </p>

                  <h5>Analyzed Engine Load Sequence</h5>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={analysisResult.sequence_data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="Timestamp" />
                      <YAxis
                        label={{
                          value: "Engine Load %",
                          angle: -90,
                          position: "insideLeft",
                        }}
                      />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="EngineLoad"
                        stroke="#8884d8"
                        name="Actual Load"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VehicleView;
