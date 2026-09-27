import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import ActiveSession from "./pages/ActiveSession";
import "./App.css";

// Placeholder for other pages
const Placeholder = ({ title }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100%",
    }}
  >
    <h1 style={{ color: "var(--text-tertiary)" }}>{title}</h1>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="sessions" element={<ActiveSession />} />
          <Route
            path="classrooms"
            element={<Placeholder title="Classrooms" />}
          />
          <Route path="analytics" element={<Placeholder title="Analytics" />} />
          <Route path="settings" element={<Placeholder title="Settings" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
