import { useEffect, useState } from "react";
import Workshop from "./views/Workshop";

function useHealth(intervalMs = 15000): boolean {
  const [ok, setOk] = useState(true);
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const ctl = new AbortController();
        const timeout = window.setTimeout(() => ctl.abort(), 3000);
        const r = await fetch("/api/health", { signal: ctl.signal, cache: "no-store" });
        window.clearTimeout(timeout);
        if (!cancelled) setOk(r.ok);
      } catch {
        if (!cancelled) setOk(false);
      }
    };
    check();
    const handle = window.setInterval(check, intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [intervalMs]);
  return ok;
}

export default function App() {
  return (
    <div className="flex h-full flex-col bg-canvas text-ink">
      <Header />
      <main className="mx-auto flex w-full max-w-[1560px] flex-1 min-h-0 flex-col px-5 pb-5">
        <Workshop />
      </main>
    </div>
  );
}

function Header() {
  const connected = useHealth();
  return (
    <header className="mx-auto flex w-full max-w-[1560px] shrink-0 items-center justify-between px-5 pb-3 pt-4">
      <div className="flex items-center gap-2.5">
        <LogoMark />
        <div className="flex items-baseline gap-2">
          <span className="font-display text-[15px] font-semibold tracking-[-0.01em] text-ink">
            Workshop
          </span>
          <span className="hidden text-[12px] font-medium text-muted-2 sm:inline">
            asset-factory
          </span>
        </div>
      </div>
      <div
        className={
          "flex items-center gap-2 rounded-pill border px-2.5 py-1 text-[11.5px] font-medium transition-colors " +
          (connected
            ? "border-accent-green/20 bg-accent-green/[0.07] text-accent-green"
            : "border-accent-red/20 bg-accent-red/[0.07] text-accent-red")
        }
      >
        <span className="relative flex h-2 w-2">
          {connected && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-green/40" />
          )}
          <span
            className={
              "relative inline-flex h-2 w-2 rounded-full " +
              (connected ? "bg-accent-green" : "bg-accent-red")
            }
          />
        </span>
        {connected ? "Connected" : "Disconnected"}
      </div>
    </header>
  );
}

function LogoMark() {
  return (
    <div className="grid h-7 w-7 place-items-center rounded-[8px] bg-ink text-paper shadow-card">
      <svg width="16" height="16" viewBox="0 0 22 22" fill="none" aria-hidden>
        <path
          d="M6 14.5L11 5.5L16 14.5"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M8 11h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    </div>
  );
}
