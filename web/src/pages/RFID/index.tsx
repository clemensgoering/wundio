import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Button, Card, Modal, Input, Select, Spinner, Badge } from "@/components/ui";
import type { RfidTag, User } from "@/types/api";

const TAG_TYPES = ["user", "playlist", "action"] as const;
const ACTIONS   = ["stop", "vol_up", "vol_down", "sleep_timer"] as const;

const typeBadge: Record<string, "amber"|"teal"|"muted"> = {
  user: "amber", playlist: "teal", action: "muted"
};

export default function RfidPage() {
  const { data: tags,  mutate: mutateTags  } = useSWR<RfidTag[]>("tags",  () => api.listTags()  as Promise<RfidTag[]>);
  const { data: users                       } = useSWR<User[]>("users",   () => api.listUsers() as Promise<User[]>);
  const [modal,    setModal]   = useState(false);
  const [scanning, setScanning] = useState(false);
  const [loading,  setLoading] = useState(false);
  const [error,    setError]   = useState("");

  const [form, setForm] = useState({
    uid: "", label: "", tag_type: "playlist" as typeof TAG_TYPES[number],
    user_id: "", spotify_uri: "", action: "stop" as typeof ACTIONS[number],
  });

  const patch = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  const openModal = () => { setForm({ uid:"", label:"", tag_type:"playlist", user_id:"", spotify_uri:"", action:"stop" }); setError(""); setModal(true); };

  const mockScan = async () => {
    setScanning(true);
    try {
      const uid = Math.random().toString(16).slice(2, 10).toUpperCase();
      patch("uid", uid);
    } finally { setScanning(false); }
  };

  const save = async () => {
    if (!form.uid || !form.label) { setError("UID und Label erforderlich"); return; }
    setLoading(true); setError("");
    try {
      const body: Record<string, string|number|null> = { uid: form.uid, label: form.label, tag_type: form.tag_type };
      if (form.tag_type === "user")     body.user_id     = parseInt(form.user_id) || null;
      if (form.tag_type === "playlist") body.spotify_uri = form.spotify_uri || null;
      if (form.tag_type === "action")   body.action      = form.action;
      await api.assignTag(body);
      await mutateTags(); setModal(false);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const remove = async (uid: string) => {
    if (!confirm("Tag entfernen?")) return;
    await api.deleteTag(uid); mutateTags();
  };

  return (
    <div className="max-w-3xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-extrabold text-3xl text-paper mb-1">RFID Tags</h1>
          <p className="text-muted text-sm">Figuren, Karten und Aktions-Tags verwalten</p>
        </div>
        <Button onClick={openModal}>+ Tag zuweisen</Button>
      </div>

      {!tags ? <Spinner /> : tags.length === 0 ? (
        <Card className="p-10 text-center">
          <p className="text-4xl mb-3">⬡</p>
          <p className="text-muted">Noch keine Tags zugewiesen. Halte eine Karte/Figur an den Reader und weise sie hier zu.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {tags.map(t => (
            <Card key={t.uid} className="flex items-center gap-4 p-4">
              <div className="w-10 h-10 rounded-xl bg-surface border border-border flex items-center justify-center text-lg flex-shrink-0">
                {t.tag_type === "user" ? "👤" : t.tag_type === "playlist" ? "🎵" : "⚡"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <p className="font-display font-semibold text-paper text-sm">{t.label}</p>
                  <Badge color={typeBadge[t.tag_type]}>{t.tag_type}</Badge>
                </div>
                <p className="text-xs font-mono text-muted">{t.uid}</p>
                {t.spotify_uri  && <p className="text-xs text-teal/70 truncate mt-0.5">{t.spotify_uri}</p>}
                {t.action       && <p className="text-xs text-amber/70 mt-0.5">Aktion: {t.action}</p>}
              </div>
              <Button variant="danger" size="sm" onClick={() => remove(t.uid)}>✕</Button>
            </Card>
          ))}
        </div>
      )}

      {modal && (
        <Modal title="Tag zuweisen" onClose={() => setModal(false)}>
          <div className="space-y-4">
            {/* UID */}
            <div className="flex gap-2">
              <Input label="Tag UID" placeholder="Halte Tag an Reader…" value={form.uid}
                     onChange={e => patch("uid", e.target.value.toUpperCase())} className="flex-1" />
              <div className="flex flex-col justify-end">
                <Button variant="secondary" size="sm" loading={scanning} onClick={mockScan}>🎲 Mock</Button>
              </div>
            </div>

            <Input label="Label" placeholder="z.B. Elsa-Figur" value={form.label}
                   onChange={e => patch("label", e.target.value)} />

            <Select label="Typ" value={form.tag_type} onChange={e => patch("tag_type", e.target.value)}>
              {TAG_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </Select>

            {form.tag_type === "user" && (
              <Select label="Kind" value={form.user_id} onChange={e => patch("user_id", e.target.value)}>
                <option value="">— Auswählen —</option>
                {users?.map(u => <option key={u.id} value={u.id}>{u.display_name}</option>)}
              </Select>
            )}
            {form.tag_type === "playlist" && (
              <Input label="Spotify Playlist URI" placeholder="spotify:playlist:…" value={form.spotify_uri}
                     onChange={e => patch("spotify_uri", e.target.value)} />
            )}
            {form.tag_type === "action" && (
              <Select label="Aktion" value={form.action} onChange={e => patch("action", e.target.value)}>
                {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
              </Select>
            )}

            {error && <p className="text-xs text-red-400">{error}</p>}
            <div className="flex gap-2 justify-end pt-2">
              <Button variant="secondary" onClick={() => setModal(false)}>Abbrechen</Button>
              <Button loading={loading} onClick={save}>Speichern</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
