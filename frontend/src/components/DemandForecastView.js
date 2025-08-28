import React, { useState } from "react";
import axios from "axios";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const API_BASE_URL = "http://127.0.0.1:5000/api";

const DemandForecastView = ({ navigateTo }) => {
  const [forecastData, setForecastData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRunForecast = () => {
    setIsLoading(true);
    setError("");
    setForecastData(null);
    axios
      .post(`${API_BASE_URL}/predict-demand`)
      .then((res) => {
        setForecastData(res.data);
      })
      .catch((err) => {
        console.error("Error running forecast:", err);
        setError(
          "Could not run the demand forecast. Please check the console."
        );
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  const chartData = forecastData
    ? {
        labels: forecastData.map((d) => d.ds),
        datasets: [
          {
            label: "Actual Demand",
            data: forecastData.map((d) => d.actual),
            borderColor: "rgba(0, 0, 0, 0.6)",
            backgroundColor: "rgba(0, 0, 0, 0.1)",
            borderWidth: 2,
            pointRadius: 1,
          },
          {
            label: "Hybrid Prophet-LSTM Forecast",
            data: forecastData.map((d) => d.yhat),
            borderColor: "rgba(255, 99, 132, 1)",
            backgroundColor: "rgba(255, 99, 132, 0.2)",
            borderWidth: 2,
            pointRadius: 1,
            fill: true,
          },
        ],
      }
    : null;

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: "top",
      },
      title: {
        display: true,
        text: "Equipment Demand Forecast vs. Actuals",
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Date",
        },
      },
      y: {
        title: {
          display: true,
          text: "Rental Units",
        },
      },
    },
  };

  return (
    <div className="view-container">
      <button className="back-button" onClick={() => navigateTo("dashboard")}>
        &larr; Back to Dashboard
      </button>
      <h2>Demand Forecasting</h2>
      <div className="forecast-controls">
        <p>
          This module uses a Hybrid Prophet-LSTM model to forecast equipment
          demand for the next 90 days.
        </p>
        <button onClick={handleRunForecast} disabled={isLoading}>
          {isLoading ? "Running Forecast..." : "Run New Forecast"}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {chartData && (
        <div className="chart-container">
          <Line options={chartOptions} data={chartData} />
        </div>
      )}
    </div>
  );
};

export default DemandForecastView;
