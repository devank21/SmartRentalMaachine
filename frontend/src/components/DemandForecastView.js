import React, { useState } from "react";
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
import "./DemandForecastView.css";

function DemandForecastView() {
  const [forecastData, setForecastData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchForecast = async () => {
    setIsLoading(true);
    setError(null);
    setForecastData(null); // Clear previous results
    try {
      const response = await fetch("http://localhost:5000/api/predict-demand", {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        // If server returned an error, use the error message from the JSON response
        throw new Error(data.error || "Network response was not ok");
      }

      // Ensure the received data is an array before setting the state
      if (Array.isArray(data)) {
        setForecastData(data);
      } else {
        // If data is not an array, something is wrong with the API response format
        console.error("API response is not an array:", data);
        throw new Error("Received invalid data format from the server.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="demand-forecast-view">
      <h2>Demand Forecast Analysis</h2>
      <button onClick={fetchForecast} disabled={isLoading}>
        {isLoading ? "Forecasting..." : "Run Forecast"}
      </button>

      {error && <p className="error-message">Error: {error}</p>}

      {forecastData && forecastData.length > 0 && (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={forecastData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="ds" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="yhat"
                stroke="#8884d8"
                name="Forecast"
              />
              <Line
                type="monotone"
                dataKey="y"
                stroke="#82ca9d"
                name="Historical"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {forecastData && forecastData.length === 0 && (
        <p>No forecast data available.</p>
      )}
    </div>
  );
}

export default DemandForecastView;
