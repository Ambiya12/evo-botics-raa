import React from "react";
import ReactDOM from "react-dom/client";
import { AdminDashboard } from "./app/AdminDashboard";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AdminDashboard />
  </React.StrictMode>
);
