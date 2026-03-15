const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const api = {
  // System
  status:        () => req("/system/status"),
  completeSetup: () => req("/system/complete-setup", { method: "POST" }),

  // Users
  listUsers:   () => req("/users/"),
  createUser:  (body: object) => req("/users/", { method: "POST", body: JSON.stringify(body) }),
  updateUser:  (id: number, body: object) => req(`/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteUser:  (id: number) => req(`/users/${id}`, { method: "DELETE" }),

  // RFID
  listTags:   () => req("/rfid/"),
  assignTag:  (body: object) => req("/rfid/assign", { method: "POST", body: JSON.stringify(body) }),
  deleteTag:  (uid: string) => req(`/rfid/${uid}`, { method: "DELETE" }),
  mockScan:   (uid: string) => req(`/rfid/mock-scan/${uid}`, { method: "POST" }),

  // Playback
  playbackState: () => req("/playback/state"),
  setVolume:     (vol: number) => req("/playback/volume", { method: "POST", body: JSON.stringify({ volume: vol }) }),
  setActiveUser: (id: number) => req("/playback/active-user", { method: "POST", body: JSON.stringify({ user_id: id }) }),
  pressButton:   (name: string) => req(`/playback/button/${name}`, { method: "POST" }),

  // Settings
  getSetting: (key: string) => req(`/settings/${key}`),
  setSetting: (key: string, value: string) => req(`/settings/${key}`, { method: "PUT", body: JSON.stringify({ value }) }),
};
