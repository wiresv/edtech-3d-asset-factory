import { useEffect, useState } from "react";
import Workshop from "./views/Workshop";
import Review from "./views/Review";

type Route = { view: "workshop" } | { view: "review"; run: string | null };

function parseRoute(): Route {
  const path = window.location.pathname.replace(/\/+$/, "");
  if (path === "/review" || path === "/review.html") {
    const run = new URLSearchParams(window.location.search).get("run");
    return { view: "review", run };
  }
  return { view: "workshop" };
}

export default function App() {
  const [route, setRoute] = useState<Route>(parseRoute);

  useEffect(() => {
    const onPop = () => setRoute(parseRoute());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  return (
    <div className="flex h-full flex-col bg-paper text-ink">
      <Header active={route.view} />
      <main className="mx-auto flex w-full max-w-[1480px] flex-1 min-h-0 flex-col px-6 pb-6">
        {route.view === "workshop" ? <Workshop /> : <Review runPath={route.run} />}
      </main>
    </div>
  );
}

function Header({ active }: { active: "workshop" | "review" }) {
  return (
    <header className="mx-auto flex w-full max-w-[1480px] shrink-0 items-center justify-between px-6 pt-5 pb-4">
      <div className="flex items-center gap-2.5">
        <LogoMark />
        <div className="flex items-baseline gap-2">
          <span className="font-display text-[15px] font-semibold tracking-tight text-ink">
            Workshop
          </span>
          <span className="text-[12px] font-medium text-muted-2">
            asset-factory
          </span>
        </div>
      </div>
      <nav className="flex items-center gap-0.5 rounded-pill border border-line bg-card p-0.5">
        <NavTab href="/" current={active === "workshop"} label="Generate" />
        <NavTab href="/review" current={active === "review"} label="Review" />
      </nav>
      <div className="flex items-center gap-2 text-[12px] text-muted">
        <span className="inline-flex h-2 w-2 rounded-full bg-accent-green" />
        <span>Connected</span>
      </div>
    </header>
  );
}

function NavTab({ href, current, label }: { href: string; current: boolean; label: string }) {
  return (
    <a
      href={href}
      className={
        "rounded-pill px-3.5 py-1 text-[13px] font-medium transition-all " +
        (current
          ? "bg-ink text-paper shadow-card"
          : "text-muted hover:text-ink")
      }
    >
      {label}
    </a>
  );
}

function LogoMark() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 22 22"
      fill="none"
      aria-hidden
      className="text-ink"
    >
      <rect
        x="1.5"
        y="1.5"
        width="19"
        height="19"
        rx="5"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <path
        d="M6.5 14.5L11 5.5L15.5 14.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M8.25 11h5.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}
