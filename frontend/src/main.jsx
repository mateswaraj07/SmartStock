import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import "./styles.css";
import App from "./App.jsx";
import { AuthProvider } from "./auth.jsx";
import { ToastHost } from "./ui.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <AuthProvider>
      <App />
      <ToastHost />
    </AuthProvider>
  </BrowserRouter>
);
