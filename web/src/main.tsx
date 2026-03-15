import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import Dashboard from "@/pages/Dashboard";
import Users     from "@/pages/Users";
import RfidPage  from "@/pages/RFID";
import Playback  from "@/pages/Playback";
import Settings  from "@/pages/Settings";
import LogPage   from "@/pages/Log";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/"         element={<Dashboard />} />
          <Route path="/playback" element={<Playback />}  />
          <Route path="/users"    element={<Users />}     />
          <Route path="/rfid"     element={<RfidPage />}  />
          <Route path="/settings" element={<Settings />}  />
          <Route path="/log"      element={<LogPage />}   />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  </React.StrictMode>
);