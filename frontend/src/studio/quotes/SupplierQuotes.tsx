import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { ArrowLeft, FileText, Plus } from "lucide-react";
import type { ProductPart } from "../../product-flow/types.ts";
import "./quotes.css";

const FIELDS = [
  ["unit_price", "Unit price"],
  ["currency", "Currency"],
  ["quantity", "Quoted quantity"],
  ["minimum_order", "Minimum order"],
  ["lead_time", "Lead time"],
  ["delivery_date", "Delivery date"],
  ["shipping", "Shipping terms"],
  ["destination", "Destination"],
  ["quote_date", "Quote date"],
  ["valid_until", "Valid until"],
  ["part_number", "Part number"],
  ["revision", "Revision"],
  ["material", "Material"],
  ["certificates", "Certificates and documents"],
  ["exceptions", "Supplier exceptions"],
] as const;
type Field = (typeof FIELDS)[number][0];
type Term = {
  value: string;
  excerpt: string | null;
  page: number | null;
  origin: "extracted" | "buyer_review";
};
type Quote = {
  quote_id: string;
  part_id: string;
  supplier: string;
  filename: string;
  source_kind: "pdf" | "reply";
  source_url: string;
  source_text: string;
  created_at: string;
  version: number;
  reviewed: boolean;
  terms: Partial<Record<Field, Term>>;
  issues: string[];
  follow_up: string;
};
type Collection = {
  project_name: string;
  parts: ProductPart[];
  quotes: Quote[];
};

async function readQuotes(
  url: string,
  options?: RequestInit,
): Promise<Collection> {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(
      body?.message ??
        body?.detail?.message ??
        "Quotes could not be loaded or saved. Try again.",
    );
  }
  return body;
}

const importedAt = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});
const errorText = (cause: unknown) =>
  cause instanceof Error ? cause.message : "Something went wrong. Try again.";

export function SupplierQuotes({
  projectId,
  initialPart,
  onBack,
}: {
  projectId: string;
  initialPart?: string;
  onBack?: () => void;
}) {
  const url = `/api/v1/products/${encodeURIComponent(projectId)}/quotes`;
  const [collection, setCollection] = useState<Collection | null>(null);
  const [partId, setPartId] = useState(initialPart ?? "");
  const [source, setSource] = useState<"pdf" | "reply">("pdf");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const [comparison, setComparison] = useState<[string, string] | null>(null);
  const headingId = useId();
  const partNumberId = useId();

  useEffect(() => {
    const controller = new AbortController();
    readQuotes(url, { signal: controller.signal })
      .then((result) => {
        setCollection(result);
        setPartId((current) =>
          result.parts.some((part) => part.part_id === current)
            ? current
            : (result.quotes.findLast((quote) =>
                result.parts.some((part) => part.part_id === quote.part_id),
              )?.part_id ??
              result.parts[0]?.part_id ??
              ""),
        );
        setError("");
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(errorText(cause));
      });
    return () => controller.abort();
  }, [url, retry]);

  async function importQuote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const updated = await readQuotes(url, {
        method: "POST",
        body: new FormData(form),
      });
      const added = updated.quotes.find(
        (quote) =>
          !collection?.quotes.some((old) => old.quote_id === quote.quote_id),
      );
      if (added) {
        const prior = [...updated.quotes]
          .reverse()
          .find(
            (quote) =>
              quote.part_id === partId && quote.quote_id !== added.quote_id,
          );
        setComparison([added.quote_id, prior?.quote_id ?? ""]);
      }
      setCollection(updated);
      form.reset();
      setNotice(
        added
          ? "Quote imported. Review the extracted terms against the source."
          : "This quote is already saved.",
      );
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(false);
    }
  }

  async function saveReview(quote: Quote, terms: Record<string, string>) {
    const updated = await readQuotes(`${url}/${quote.quote_id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_version: quote.version, terms }),
    });
    setCollection(updated);
    setNotice(`Review saved for ${quote.supplier}.`);
  }

  const part = collection?.parts.find((item) => item.part_id === partId);
  const quotes =
    collection?.quotes.filter((quote) => quote.part_id === partId).reverse() ??
    [];
  const first =
    quotes.find((quote) => quote.quote_id === comparison?.[0]) ?? quotes[0];
  const second =
    quotes.find(
      (quote) => quote.quote_id === comparison?.[1] && quote !== first,
    ) ?? quotes.find((quote) => quote !== first);
  const compared = [first, second].filter((quote): quote is Quote =>
    Boolean(quote),
  );

  return (
    <main className="rs-quote-workspace" aria-labelledby={headingId}>
      <header className="rs-quote-heading">
        {onBack ? (
          <button type="button" className="rs-link" onClick={onBack}>
            <ArrowLeft size={16} /> Back to Studio
          </button>
        ) : (
          <a className="rs-link" href={`#project/${projectId}`}>
            <ArrowLeft size={16} /> Back to investigation
          </a>
        )}
        <h1 id={headingId} className="rs-h2">
          Supplier quotes
        </h1>
        {collection && <p className="rs-small">{collection.project_name}</p>}
      </header>
      {!collection &&
        (error ? (
          <div role="alert" className="rs-quote-message">
            <p>{error}</p>
            <button
              type="button"
              className="rs-btn rs-btn-sm"
              onClick={() => {
                setError("");
                setRetry((value) => value + 1);
              }}
            >
              Try again
            </button>
          </div>
        ) : (
          <p role="status" className="rs-small">
            Loading supplier quotes…
          </p>
        ))}
      {collection && !part && (
        <p className="rs-small">
          Add a part to this investigation before importing supplier quotes.
        </p>
      )}
      {part && (
        <div className="rs-quote-layout">
          <section className="rs-quote-intake" aria-label="Import a quote">
            <h2 className="rs-h3">Import a quote</h2>
            <form onSubmit={importQuote} key={partId}>
              <label>
                Part
                <select
                  className="rs-select"
                  aria-label="Part"
                  aria-describedby={part.part_number ? partNumberId : undefined}
                  value={partId}
                  disabled={busy}
                  onChange={(event) => {
                    setPartId(event.target.value);
                    setComparison(null);
                    setError("");
                    setNotice("");
                  }}
                >
                  {collection?.parts.map((item) => (
                    <option key={item.part_id} value={item.part_id}>
                      {item.name}
                    </option>
                  ))}
                </select>
                {part.part_number && (
                  <span className="rs-small rs-mono" id={partNumberId}>
                    {part.part_number}
                  </span>
                )}
              </label>
              <input type="hidden" name="part_id" value={partId} />
              <label>
                Supplier
                <input
                  className="rs-input"
                  name="supplier"
                  autoComplete="organization"
                  placeholder="Supplier name"
                  required
                  maxLength={160}
                />
              </label>
              <fieldset className="rs-quote-source-picker">
                <legend>Source</legend>
                <label>
                  <input
                    type="radio"
                    name="quote-source"
                    checked={source === "pdf"}
                    onChange={() => setSource("pdf")}
                  />{" "}
                  Quote PDF
                </label>
                <label>
                  <input
                    type="radio"
                    name="quote-source"
                    checked={source === "reply"}
                    onChange={() => setSource("reply")}
                  />{" "}
                  Paste reply
                </label>
              </fieldset>
              {source === "pdf" ? (
                <label>
                  Quote PDF
                  <input
                    className="rs-input rs-quote-file"
                    type="file"
                    name="file"
                    accept="application/pdf,.pdf"
                    required
                  />
                  <span className="rs-small">Text PDF, up to 4 MB</span>
                </label>
              ) : (
                <label>
                  Supplier reply
                  <textarea
                    className="rs-input"
                    name="reply"
                    rows={6}
                    maxLength={100000}
                    placeholder="Paste the supplier’s reply, including quoted terms."
                    required
                  />
                </label>
              )}
              <button
                className="rs-btn rs-btn-grad"
                type="submit"
                disabled={busy}
              >
                <Plus size={16} /> {busy ? "Importing…" : "Import quote"}
              </button>
              {error && (
                <p className="rs-quote-error" role="alert">
                  {error}
                </p>
              )}
            </form>
          </section>
          <section
            className="rs-quote-comparison"
            aria-label="Quote comparison"
          >
            <h2 className="rs-h3">Compare quotes</h2>
            <p className="rs-small" role="status">
              {notice}
            </p>
            {quotes.length === 0 ? (
              <p className="rs-small">
                Import a quote for {part.name} to see its terms here.
              </p>
            ) : (
              <>
                {quotes.length > 2 && (
                  <div className="rs-quote-selectors">
                    {[first, second].map((quote, index) => (
                      <label key={index}>
                        Quote {index + 1}
                        <select
                          className="rs-select"
                          value={quote?.quote_id}
                          onChange={(event) => {
                            const other = index === 0 ? second : first;
                            const next = event.target.value;
                            const otherId =
                              next === other?.quote_id
                                ? quote?.quote_id
                                : other?.quote_id;
                            setComparison(
                              index === 0
                                ? [next, otherId ?? ""]
                                : [otherId ?? "", next],
                            );
                          }}
                        >
                          {quotes.map((option) => (
                            <option
                              key={option.quote_id}
                              value={option.quote_id}
                            >
                              {option.supplier} ·{" "}
                              {importedAt.format(new Date(option.created_at))}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </div>
                )}
                <table
                  className="rs-table rs-quote-table"
                  aria-label={`Supplier quotes for ${part.name}`}
                >
                  <thead>
                    <tr>
                      <th scope="col">Terms</th>
                      {compared.map((quote) => (
                        <th scope="col" key={quote.quote_id}>
                          <span className="rs-quote-supplier">
                            {quote.supplier}
                          </span>
                          <span className="rs-small">
                            {quote.reviewed ? "Reviewed" : "Needs review"} ·{" "}
                            {quote.source_kind === "pdf" ? "PDF" : "Reply"}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {FIELDS.map(([field, label]) => (
                      <tr key={field}>
                        <th scope="row">{label}</th>
                        {compared.map((quote) => (
                          <td key={quote.quote_id}>
                            {quote.terms[field]?.value || (
                              <span className="rs-quote-missing">
                                Not supplied
                              </span>
                            )}
                            {quote.terms[field]?.origin === "buyer_review" && (
                              <span className="rs-quote-supplier-note rs-small">
                                Buyer edit
                              </span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                    <tr>
                      <th scope="row">Follow-up</th>
                      {compared.map((quote) => (
                        <td key={quote.quote_id}>
                          {quote.issues.length ? (
                            <ul className="rs-quote-issues">
                              {quote.issues.map((issue) => (
                                <li key={issue}>{issue}</li>
                              ))}
                            </ul>
                          ) : (
                            "No gaps flagged"
                          )}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
                <div className="rs-quote-evidence">
                  {compared.map((quote) => (
                    <QuoteEvidence
                      key={quote.quote_id}
                      quote={quote}
                      onSave={saveReview}
                    />
                  ))}
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </main>
  );
}

function QuoteEvidence({
  quote,
  onSave,
}: {
  quote: Quote;
  onSave: (quote: Quote, terms: Record<string, string>) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [copyStatus, setCopyStatus] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setSaving(true);
    setError("");
    try {
      await onSave(
        quote,
        Object.fromEntries(
          FIELDS.map(([key]) => [key, String(values.get(key) ?? "")]),
        ),
      );
      setEditing(false);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setSaving(false);
    }
  }

  return (
    <details>
      <summary>Review source · {quote.supplier}</summary>
      <div className="rs-quote-evidence-body">
        <a
          className="rs-link"
          href={quote.source_url}
          target="_blank"
          rel="noreferrer"
        >
          <FileText size={16} /> {quote.filename}
        </a>
        <p className="rs-small">
          Imported {importedAt.format(new Date(quote.created_at))}
        </p>
        <dl className="rs-quote-excerpts">
          {FIELDS.map(([key, label]) => {
            const term = quote.terms[key];
            if (!term) return null;
            return (
              <div key={key}>
                <dt>
                  {label}
                  {term.origin === "buyer_review" && " · Buyer edit"}
                </dt>
                <dd>
                  {quote.source_kind === "pdf" && term.page
                    ? `Page ${term.page} · `
                    : ""}
                  {term.excerpt ?? "Entered during review"}
                </dd>
              </div>
            );
          })}
        </dl>
        <details className="rs-quote-raw">
          <summary>Full source text</summary>
          <pre>{quote.source_text}</pre>
        </details>
        {editing ? (
          <form className="rs-quote-review" onSubmit={submit}>
            {FIELDS.map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  className="rs-input"
                  name={key}
                  defaultValue={quote.terms[key]?.value ?? ""}
                  maxLength={1000}
                />
              </label>
            ))}
            <div className="rs-quote-actions">
              <button
                type="submit"
                className="rs-btn rs-btn-solid rs-btn-sm"
                disabled={saving}
              >
                {saving ? "Saving…" : "Save review"}
              </button>
              <button
                type="button"
                className="rs-btn rs-btn-ghost rs-btn-sm"
                disabled={saving}
                onClick={() => setEditing(false)}
              >
                Cancel
              </button>
            </div>
            {error && (
              <p className="rs-quote-error" role="alert">
                {error}
              </p>
            )}
          </form>
        ) : (
          <button
            type="button"
            className="rs-btn rs-btn-sm"
            onClick={() => setEditing(true)}
          >
            Review terms
          </button>
        )}
        <details className="rs-quote-raw">
          <summary>Follow-up draft</summary>
          <pre>{quote.follow_up}</pre>
          <button
            type="button"
            className="rs-btn rs-btn-sm"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(quote.follow_up);
                setCopyStatus("Draft copied.");
              } catch {
                setCopyStatus("Select the draft text to copy it.");
              }
            }}
          >
            Copy draft
          </button>
          <span className="rs-small" role="status">
            {copyStatus}
          </span>
        </details>
      </div>
    </details>
  );
}

export function QuoteDialog({
  projectId,
  partId,
  onClose,
}: {
  projectId: string;
  partId?: string;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  const close = () => {
    dialog.current?.close();
    onClose();
  };
  return (
    <dialog
      ref={dialog}
      className="rs-quote-dialog"
      aria-label="Supplier quotes"
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
    >
      <SupplierQuotes
        projectId={projectId}
        initialPart={partId}
        onBack={close}
      />
    </dialog>
  );
}
