import type { Metadata } from "next";
import { QuickstartClient } from "./Quickstartclient";

export const metadata: Metadata = {
  title: "Quickstart – Wundio einrichten",
  description: "Schritt-für-Schritt Anleitung zum Einrichten deiner Wundio Box auf dem Raspberry Pi."
};

export default function QuickstartPage() {
  return <QuickstartClient />;
}