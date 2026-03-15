import type { Metadata } from "next";
import { HardwareGuideClient } from "./HardwareGuideClient";

export const metadata: Metadata = {
  title: "Hardware Aufbau",
  description: "Interaktive Schritt-für-Schritt Anleitung zum Aufbau deiner Wundio Box.",
};

export default function AufbauPage() {
  return <HardwareGuideClient />;
}