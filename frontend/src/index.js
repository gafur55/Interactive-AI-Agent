import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import TavusTestPage from "./pages/TavusTestPage";
import { CVIProvider } from "./components/cvi/components/cvi-provider";

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <CVIProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/tavus" element={<TavusTestPage />} />
        </Routes>
      </BrowserRouter>
    </CVIProvider>
  </React.StrictMode>
);
