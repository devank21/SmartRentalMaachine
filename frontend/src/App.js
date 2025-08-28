import React, { useState } from "react";
import Dashboard from "./components/Dashboard";
import CategoryView from "./components/CategoryView";
import VehicleView from "./components/VehicleView";
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
      case "dashboard":
      default:
        return <Dashboard navigateTo={navigateTo} />;
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 onClick={() => navigateTo("dashboard")}>Smart Rental Fleet</h1>
      </header>
      <main className="main-content">{renderView()}</main>
    </div>
  );
}

export default App;
