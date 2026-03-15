import { Nav }    from "@/components/Nav";
import { Footer } from "@/components/Footer";

const DOC_SECTIONS = [
  {
    title: "Einstieg",
    links: [
      { href: "/docs",              label: "Übersicht"         },
      { href: "/docs/aufbau",       label: "Hardware Aufbau"   },
      { href: "/docs/quickstart",   label: "Installation"      },
      { href: "/docs/hardware",     label: "Pinout Referenz"   },
      { href: "/docs/faq",          label: "FAQ"               },
    ],
  },
  {
    title: "Phasen",
    links: [
      { href: "/docs/phase/0", label: "Phase 0 – Fundament" },
      { href: "/docs/phase/1", label: "Phase 1 – Musik"     },
      { href: "/docs/phase/2", label: "Phase 2 – Multi-User"},
      { href: "/docs/phase/3", label: "Phase 3 – KI & Sprache" },
    ],
  },
  {
    title: "Referenz",
    links: [
      { href: "/hardware",  label: "GPIO Pinout"     },
      { href: "/modules",   label: "Module"          },
    ],
  },
];

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Nav />
      <div className="max-w-5xl mx-auto px-6 pt-28 pb-24">
        <div className="flex gap-10">
          {/* Sidebar */}
          <aside className="hidden md:block w-52 flex-shrink-0">
            <div className="sticky top-24 space-y-6">
              {DOC_SECTIONS.map(section => (
                <div key={section.title}>
                  <p className="text-xs font-display font-black text-muted uppercase tracking-widest mb-2">
                    {section.title}
                  </p>
                  <div className="space-y-0.5">
                    {section.links.map(link => (
                      <a key={link.href} href={link.href}
                         className="block px-3 py-2 rounded-xl text-sm font-body text-charcoal
                                    hover:bg-sand hover:text-ink transition-colors duration-150">
                        {link.label}
                      </a>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </aside>

          {/* Content */}
          <main className="flex-1 min-w-0">
            {children}
          </main>
        </div>
      </div>
      <Footer />
    </>
  );
}