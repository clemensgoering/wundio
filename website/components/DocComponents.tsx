// Shared doc page primitives

export function DocHeader({ chip, title, desc }: {
  chip: string; title: string; desc: string;
}) {
  return (
    <div className="mb-10">
      <span className="inline-block bg-honey/12 text-honey border border-honey/20
                       text-xs font-display font-bold uppercase tracking-widest
                       px-3.5 py-1 rounded-full mb-4">
        {chip}
      </span>
      <h1 className="font-display font-black text-4xl text-ink mb-3">{title}</h1>
      <p className="text-muted font-body text-lg leading-relaxed max-w-xl">{desc}</p>
    </div>
  );
}

export function Step({ num, title, children, code }: {
  num: string; title: string; children: React.ReactNode; code?: string;
}) {
  return (
    <div className="flex gap-5 mb-10">
      <span className="font-display font-black text-5xl text-honey/25 w-14 flex-shrink-0 leading-none select-none">
        {num}
      </span>
      <div className="flex-1">
        <h2 className="font-display font-bold text-xl text-ink mb-2">{title}</h2>
        <div className="text-muted text-sm leading-relaxed font-body mb-3">{children}</div>
        {code && <CodeBlock>{code}</CodeBlock>}
      </div>
    </div>
  );
}

export function CodeBlock({ children, lang = "bash" }: { children: string; lang?: string }) {
  return (
    <div className="bg-ink rounded-2xl px-5 py-4 font-mono text-sm text-white/85 overflow-x-auto shadow-soft">
      <span className="text-honey/50 select-none mr-2">$</span>
      <span className="select-all">{children}</span>
    </div>
  );
}

export function InfoBox({ icon, title, children, color = "honey" }: {
  icon: string; title: string; children: React.ReactNode; color?: "honey"|"coral"|"mint";
}) {
  const cls = {
    honey: "bg-honey/8 border-honey/20 text-honey",
    coral: "bg-coral/8 border-coral/20 text-coral",
    mint:  "bg-mint/8  border-mint/20  text-mint",
  }[color];
  return (
    <div className={`border rounded-2xl p-5 mb-6 ${cls}`}>
      <div className="flex gap-3 items-start">
        <span className="text-xl flex-shrink-0">{icon}</span>
        <div>
          <p className="font-display font-bold text-sm mb-1">{title}</p>
          <div className="text-sm opacity-80 font-body leading-relaxed">{children}</div>
        </div>
      </div>
    </div>
  );
}

export function PartTable({ parts }: {
  parts: { name: string; qty: string; note: string }[];
}) {
  return (
    <div className="border border-border rounded-3xl overflow-hidden mb-6">
      <table className="w-full text-sm font-body">
        <thead>
          <tr className="bg-sand border-b border-border">
            <th className="text-left py-3 px-5 font-display font-bold text-charcoal">Bauteil</th>
            <th className="text-left py-3 px-4 font-display font-bold text-charcoal w-16">Menge</th>
            <th className="text-left py-3 px-4 font-display font-bold text-charcoal">Hinweis</th>
          </tr>
        </thead>
        <tbody>
          {parts.map((p, i) => (
            <tr key={p.name} className={`border-b border-border/60 last:border-0 ${i%2===1?"bg-cream/50":""}`}>
              <td className="py-3 px-5 font-medium text-charcoal">{p.name}</td>
              <td className="py-3 px-4 text-muted">{p.qty}</td>
              <td className="py-3 px-4 text-muted">{p.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
