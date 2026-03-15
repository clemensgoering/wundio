import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Button, Card, Modal, Input, Spinner, Badge } from "@/components/ui";
import type { User } from "@/types/api";

const EMOJIS = ["🎵","🎸","🎹","🥁","🎺","🎻","🦊","🐼","🐸","🦄","🌟","🚀"];

export default function Users() {
  const { data: users, mutate } = useSWR<User[]>("users", () => api.listUsers() as Promise<User[]>);
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState({ name: "", display_name: "", avatar_emoji: "🎵", volume: 70 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const openCreate = () => {
    setForm({ name: "", display_name: "", avatar_emoji: "🎵", volume: 70 });
    setError(""); setModal("create");
  };
  const openEdit = (u: User) => {
    setEditing(u);
    setForm({ name: u.name, display_name: u.display_name, avatar_emoji: u.avatar_emoji, volume: u.volume });
    setError(""); setModal("edit");
  };
  const close = () => { setModal(null); setEditing(null); };

  const save = async () => {
    if (!form.name.trim() || !form.display_name.trim()) { setError("Name und Anzeigename erforderlich"); return; }
    setLoading(true); setError("");
    try {
      if (modal === "create") await api.createUser(form);
      else if (editing)       await api.updateUser(editing.id, form);
      await mutate(); close();
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const remove = async (u: User) => {
    if (!confirm(`„${u.display_name}" wirklich entfernen?`)) return;
    await api.deleteUser(u.id); mutate();
  };

  const activate = async (u: User) => {
    await api.setActiveUser(u.id); mutate();
  };

  return (
    <div className="max-w-3xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Kinder</h1>
          <p className="text-muted text-sm">Nutzerprofile verwalten</p>
        </div>
        <Button onClick={openCreate}>+ Kind hinzufügen</Button>
      </div>

      {!users ? <Spinner /> : users.length === 0 ? (
        <Card className="p-10 text-center">
          <p className="text-4xl mb-3">👶</p>
          <p className="text-muted">Noch keine Kinder angelegt.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {users.map(u => (
            <Card key={u.id} className="flex items-center gap-4 p-4 hover:border-border/50 transition-colors">
              {/* Avatar */}
              <div className="w-12 h-12 rounded-2xl bg-amber/10 flex items-center justify-center text-2xl flex-shrink-0">
                {u.avatar_emoji}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="font-display font-semibold text-paper">{u.display_name}</p>
                <p className="text-xs text-muted">@{u.name} · 🔊 {u.volume}%</p>
                {u.spotify_playlist_name && (
                  <p className="text-xs text-teal/70 truncate mt-0.5">🎵 {u.spotify_playlist_name}</p>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0">
                <Button variant="secondary" size="sm" onClick={() => activate(u)}>Aktivieren</Button>
                <Button variant="ghost" size="sm" onClick={() => openEdit(u)}>✎</Button>
                <Button variant="danger" size="sm" onClick={() => remove(u)}>✕</Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit modal */}
      {modal && (
        <Modal title={modal === "create" ? "Kind hinzufügen" : "Kind bearbeiten"} onClose={close}>
          <div className="space-y-4">
            <Input
              label="Benutzername (intern)"
              placeholder="z.B. max"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value.toLowerCase().replace(/\s/g,"") }))}
              disabled={modal === "edit"}
            />
            <Input
              label="Anzeigename"
              placeholder="z.B. Max"
              value={form.display_name}
              onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))}
            />

            {/* Emoji picker */}
            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-display font-medium text-muted">Avatar</span>
              <div className="flex flex-wrap gap-2">
                {EMOJIS.map(e => (
                  <button key={e}
                    onClick={() => setForm(f => ({ ...f, avatar_emoji: e }))}
                    className={`w-9 h-9 rounded-xl text-xl transition-all
                                ${form.avatar_emoji === e ? "bg-amber/20 ring-1 ring-amber/40" : "bg-surface hover:bg-surface/80"}`}
                  >{e}</button>
                ))}
              </div>
            </div>

            {/* Volume */}
            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-display font-medium text-muted">Lautstärke – {form.volume}%</span>
              <input type="range" min={0} max={100} value={form.volume}
                     onChange={e => setForm(f => ({ ...f, volume: +e.target.value }))}
                     className="accent-amber w-full" />
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}

            <div className="flex gap-2 justify-end pt-2">
              <Button variant="secondary" onClick={close}>Abbrechen</Button>
              <Button loading={loading} onClick={save}>Speichern</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
