import Workshop from "./views/Workshop";

export default function App() {
  return (
    <div className="flex h-full flex-col bg-paper text-ink">
      <Header />
      <main className="mx-auto flex w-full max-w-[1480px] flex-1 min-h-0 flex-col px-6 pb-6">
        <Workshop />
      </main>
    </div>
  );
}

function Header() {
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
      <div className="flex items-center gap-2 text-[12px] text-muted">
        <span className="inline-flex h-2 w-2 rounded-full bg-accent-green" />
        <span>Connected</span>
      </div>
    </header>
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
