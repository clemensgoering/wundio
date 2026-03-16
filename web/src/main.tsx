import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import Dashboard from "@/pages/Dashboard";
import Users     from "@/pages/Users";
import RfidPage  from "@/pages/RFID";
import Playback  from "@/pages/Playback";
import Settings  from "@/pages/Settings";
import "./index.css";
import { ErrorBoundary } from "./components/ErrorBoundary";
import LogPage from "./pages/Log";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/"         element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
          <Route path="/playback" element={<ErrorBoundary><Playback /></ErrorBoundary>}  />
          <Route path="/users"    element={<ErrorBoundary><Users /></ErrorBoundary>}     />
          <Route path="/rfid"     element={<ErrorBoundary><RfidPage /></ErrorBoundary>}  />
          <Route path="/settings" element={<ErrorBoundary><Settings /></ErrorBoundary>}  />
          <Route path="/log"      element={<ErrorBoundary><LogPage /></ErrorBoundary>}   />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  </React.StrictMode>
);