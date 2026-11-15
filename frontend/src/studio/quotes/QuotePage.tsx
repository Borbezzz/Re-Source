import "@fontsource-variable/geist-mono";
import "../studio.css";
import { SupplierQuotes } from "./SupplierQuotes.tsx";

export function QuotePage({ projectId }: { projectId: string }) {
  return (
    <div className="rs-studio rs-quote-page">
      <SupplierQuotes projectId={projectId} />
    </div>
  );
}
