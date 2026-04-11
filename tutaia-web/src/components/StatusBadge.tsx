const styles: Record<string, string> = {
  building:
    "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  running:
    "bg-green-500/10 text-green-400 border-green-500/20",
  failed:
    "bg-red-500/10 text-red-400 border-red-500/20",
};

const dots: Record<string, string> = {
  building: "bg-yellow-400 animate-pulse",
  running: "bg-green-400",
  failed: "bg-red-400",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${styles[status] ?? styles.building}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dots[status] ?? dots.building}`} />
      {status}
    </span>
  );
}
