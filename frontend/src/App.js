import React, { useState } from "react";
import Dashboard from "./components/Dashboard";
import CategoryView from "./components/CategoryView";
import VehicleView from "./components/VehicleView";
import SustainabilityView from "./components/SustainabilityView";
import BimView from "./components/BimView";
import DemandForecastView from "./components/DemandForecastView"; // Import the new component
import "./App.css";

function App() {
  const [view, setView] = useState({ name: "dashboard", props: {} });

  const navigateTo = (name, props = {}) => {
    setView({ name, props });
  };

  const renderView = () => {
    switch (view.name) {
      case "category":
        return <CategoryView {...view.props} navigateTo={navigateTo} />;
      case "vehicle":
        return <VehicleView {...view.props} navigateTo={navigateTo} />;
      case "sustainability":
        return <SustainabilityView navigateTo={navigateTo} />;
      case "bim":
        return <BimView navigateTo={navigateTo} />;
      case "demand-forecast": // Add the new view case
        return <DemandForecastView navigateTo={navigateTo} />;
      case "dashboard":
      default:
        return <Dashboard navigateTo={navigateTo} />;
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo" onClick={() => navigateTo("dashboard")}>
          CAT
        </div>
        <h1>Smart Fleet Command Center</h1>
        <nav className="main-nav">
          <a onClick={() => navigateTo("dashboard")}>Dashboard</a>
          <a onClick={() => navigateTo("sustainability")}>Sustainability</a>
          <a onClick={() => navigateTo("bim")}>BIM Viewer</a>
          <a onClick={() => navigateTo("demand-forecast")}>
            Demand Forecast
          </a>{" "}
          {/* Add the new nav link */}
        </nav>
      </header>
      <main className="main-content">{renderView()}</main>
    </div>
  );
}

export default App;
