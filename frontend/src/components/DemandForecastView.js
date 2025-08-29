import React, { useState, useEffect } from "react";
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

const API_BASE_URL = "http://localhost:5000/api";

function DemandForecastView() {
  const [forecastData, setForecastData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchForecast = () => {
    setIsLoading(true);
    setError(null);
    setForecastData(null);
    fetch(`${API_BASE_URL}/predict-demand`) // Changed to GET
      .then((res) => {
        if (!res.ok) {
          // Try to get error from response body, otherwise use status text
          return res.json().then((err) => {
            throw new Error(err.error || res.statusText);
          });
        }
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setForecastData(data);
        } else {
          throw new Error("Received invalid data format from the server.");
        }
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  // Automatically fetch forecast when the component loads
  useEffect(() => {
    fetchForecast();
  }, []);

  return (
    <div className="demand-forecast-view">
      <h2>Demand Forecast Analysis</h2>
      <p>
        Hybrid model (Prophet + LSTM) forecast of rental demand for the next 90
        days.
      </p>

      {isLoading && <div className="loading">Generating Forecast...</div>}
      {error && <p className="error-message">Error: {error}</p>}

      {forecastData && (
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
                dataKey="actual"
                name="Historical Demand"
                stroke="#82ca9d"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="yhat"
                name="Forecasted Demand"
                stroke="#8884d8"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="yhat_lower"
                name="Lower Bound"
                stroke="#ccc"
                strokeDasharray="5 5"
              />
              <Line
                type="monotone"
                dataKey="yhat_upper"
                name="Upper Bound"
                stroke="#ccc"
                strokeDasharray="5 5"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default DemandForecastView;
