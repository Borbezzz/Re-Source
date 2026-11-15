import { lazy, Suspense, useRef, useState, type CSSProperties } from "react";
import { ArrowRight, Check, ExternalLink, MapPin } from "lucide-react";
import { candidateFindings } from "./geography.ts";
import { sourceUrl } from "../api/guards.ts";
import { productApi } from "./client.ts";
import type { ProductCandidate, ProductProject } from "./types.ts";
import type { ProjectAction } from "./ProductFlow.tsx";
const ResearchGlobe = lazy(() => import("../investigation/ResearchGlobe.tsx"));
const readable = (text: string) => text.replaceAll("_", " ");
export function ProductResearch({
  project,
  busy,
  onAction,
}: {
  project: ProductProject;
  busy: string;
  onAction: ProjectAction;
}) {
  const [active, setActive] = useState<string | null>(null);
  const cards = useRef(new Map<string, HTMLElement>());
  const complete = project.research.filter(
    (job) => job.status === "complete",
  ).length;
  const failed = project.research.filter(
    (job) => job.status === "failed",
  ).length;
  const running = project.research.some(
    (job) => job.status === "queued" || job.status === "running",
  );
  const choices = Object.keys(project.selections).length;
  const findings = candidateFindings(project);
  const mappedCandidates = new Set(findings.map((finding) => finding.event_id));
  const resultCount = project.research.reduce(
    (count, job) => count + job.candidates.length,
    0,
  );
  const focusLocation = (id: string) => {
    setActive(id);
    // Scroll only the card rail, keeping the globe and the surrounding page still.
    const card = cards.current.get(id);
    const rail = card?.closest<HTMLElement>(".pf-supplier-rail");
    if (card && rail && getComputedStyle(rail).overflowY === "visible") {
      card.scrollIntoView({ block: "nearest", behavior: "instant" });
    } else if (card && rail && rail.scrollHeight > rail.clientHeight) {
      const top =
        card.getBoundingClientRect().top -
        rail.getBoundingClientRect().top +
        rail.scrollTop;
      rail.scrollTo({ top: Math.max(0, top - 16), behavior: "instant" });
    }
    card?.focus({ preventScroll: true });
  };
  return (
    <section className="pf-investigation">
      <div className="pf-section-heading">
        <div>
          <h2>Find and compare suppliers</h2>
          <p aria-live="polite">
            {complete} of {project.research.length} part investigations complete
            {failed ? ` · ${failed} need attention` : ""}.
          </p>
          <p>
            Review each result as it arrives. Choose a supplier lead after
            checking its evidence and unknowns.
          </p>
        </div>
      </div>
      <div className="pf-spatial-stage">
        <div className="pf-spatial-globe">
          <Suspense
            fallback={
              <div className="pf-globe-loading" role="status">
                Opening sourced locations…
              </div>
            }
          >
            <ResearchGlobe
              variant="immersive"
              autoRotate
              findings={findings}
              selected={active}
              onSelect={focusLocation}
              locationLabel="reported countries"
              locationNote="Country markers are representative, not supplier addresses. Demo locations are illustrative; public leads need a source."
            />
          </Suspense>
          {!findings.length ? (
            <p className="pf-unmapped-note">
              Locations will light up when sourced countries are available.
              Every result stays in the list.
            </p>
          ) : null}
        </div>
        <aside
          className="pf-supplier-rail"
          aria-label="Supplier research results"
          tabIndex={0}
        >
          <div className="pf-supplier-rail-heading">
            <h3>Supplier leads</h3>
            <span aria-live="polite">
              {resultCount
                ? `${resultCount} found`
                : running
                  ? "Searching…"
                  : "No leads yet"}
            </span>
          </div>
          {project.research.map((job) => {
            const part = project.parts.find(
              (value) => value.part_id === job.part_id,
            );
            return (
              <section className="pf-supplier-group" key={job.job_id}>
                <div className="pf-job-heading">
                  <div>
                    <h3>{part?.name ?? job.part_id}</h3>
                    {job.status !== "complete" ? (
                      <p>{readable(job.stage)}</p>
                    ) : null}
                  </div>
                  <span className={`pf-job-status pf-job-${job.status}`}>
                    {job.status === "complete"
                      ? `${job.candidates.length} leads`
                      : readable(job.status)}
                  </span>
                </div>
                {job.summary && job.status !== "complete" ? (
                  <p className="pf-job-progress">{job.summary}</p>
                ) : null}
                {!job.candidates.length &&
                (job.status === "queued" || job.status === "running") ? (
                  <p className="pf-awaiting-suppliers">
                    Supplier cards will appear here as this investigation
                    returns results.
                  </p>
                ) : null}
                {job.error ? (
                  <p className="pf-inline-error" role="alert">
                    {job.error}
                  </p>
                ) : null}
                {job.status === "failed" ? (
                  <button
                    className="secondary"
                    disabled={!!busy}
                    onClick={() =>
                      void onAction("Retrying this part…", () =>
                        productApi.investigate(
                          project.project_id,
                          [job.part_id],
                          job.mode,
                        ),
                      )
                    }
                  >
                    Retry this part
                  </button>
                ) : null}
                {!job.candidates.length && job.status === "complete" ? (
                  <p>
                    No source-backed supplier leads were found. Review the part
                    requirements or choose other parts above.
                  </p>
                ) : null}
                <div className="pf-candidates">
                  {job.candidates.map((candidate, index) => (
                    <Candidate
                      key={candidate.candidate_id}
                      candidate={candidate}
                      index={index}
                      cardRef={(element) => {
                        if (element)
                          cards.current.set(candidate.candidate_id, element);
                        else cards.current.delete(candidate.candidate_id);
                      }}
                      hasLocation={mappedCandidates.has(candidate.candidate_id)}
                      selected={
                        project.selections[job.part_id] ===
                        candidate.candidate_id
                      }
                      active={active === candidate.candidate_id}
                      busy={!!busy || job.status !== "complete"}
                      onFocus={() => setActive(candidate.candidate_id)}
                      onSelect={() =>
                        void onAction("Saving supplier choice…", () =>
                          productApi.select(
                            project.project_id,
                            job.part_id,
                            candidate.candidate_id,
                          ),
                        )
                      }
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </aside>
      </div>
      <details className="pf-activity pf-spatial-activity">
        <summary>Research activity · {project.events.length} events</summary>
        <ol>
          {project.events
            .slice(-30)
            .reverse()
            .map((event) => (
              <li key={event.sequence}>
                <time>
                  {new Date(event.created_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </time>
                <span>{event.summary}</span>
              </li>
            ))}
        </ol>
      </details>
      <div className="pf-research-continue">
        <div>
          <h3>
            {choices
              ? `${choices} supplier ${choices === 1 ? "choice" : "choices"} ready for review`
              : "Choose suppliers for your RFQ"}
          </h3>
          <p>
            {running
              ? "You can choose completed results now. Prepare the package once the remaining research finishes."
              : choices
                ? `The package will include your ${choices} selected ${choices === 1 ? "part" : "parts"}, reviewed requirements and unresolved evidence.`
                : "A public lead or sample quote still needs supplier confirmation. Your selections will form a reviewable request for quotation."}
          </p>
        </div>
        <button
          className="primary"
          disabled={!!busy || running || !choices}
          onClick={() =>
            void onAction(
              "Preparing sourcing package…",
              () => productApi.package(project.project_id),
              "approval",
            )
          }
        >
          Prepare sourcing package <ArrowRight size={16} />
        </button>
      </div>
    </section>
  );
}
function Candidate({
  candidate: c,
  index,
  cardRef,
  hasLocation,
  selected,
  active,
  busy,
  onFocus,
  onSelect,
}: {
  candidate: ProductCandidate;
  index: number;
  cardRef: (element: HTMLElement | null) => void;
  hasLocation: boolean;
  selected: boolean;
  active: boolean;
  busy: boolean;
  onFocus: () => void;
  onSelect: () => void;
}) {
  const sample = c.data_origin === "synthetic_demo";
  return (
    <article
      ref={cardRef}
      tabIndex={-1}
      aria-label={c.supplier_name}
      style={
        { "--arrival-delay": `${Math.min(index, 2) * 70}ms` } as CSSProperties
      }
      className={`pf-candidate pf-floating-candidate ${active ? "pf-candidate-active" : ""} ${selected ? "pf-candidate-selected" : ""}`}
      onFocus={onFocus}
      onPointerMove={(event) => {
        if (event.pointerType === "mouse" && !active) onFocus();
      }}
    >
      <div className="pf-candidate-heading">
        <h4>{c.supplier_name}</h4>
        <span>{sample ? "Sample quote" : "Public supplier lead"}</span>
      </div>
      <p className="pf-candidate-preview">
        {c.summary.length > 150
          ? `${c.summary.slice(0, 150).trim()}…`
          : c.summary}
      </p>
      {hasLocation ? (
        <button
          className="pf-location-action"
          onClick={onFocus}
          aria-label={`Highlight ${c.country} on the globe`}
        >
          <MapPin size={13} aria-hidden="true" />
          {c.country}
          <span>{sample ? "Demo location" : "Reported country"}</span>
        </button>
      ) : (
        <p className="pf-location">
          {c.country ? `${c.country} · not mapped` : "Location not reported"}
        </p>
      )}
      {c.price != null || c.lead_time_days != null ? (
        <dl className="pf-offer-facts">
          <div>
            <dt>{sample ? "Sample price" : "Published price"}</dt>
            <dd>
              {c.price != null
                ? `${c.currency ?? ""} ${c.price.toLocaleString()}`
                : "Not provided"}
            </dd>
          </div>
          <div>
            <dt>{sample ? "Sample lead time" : "Published lead time"}</dt>
            <dd>
              {c.lead_time_days != null
                ? `${c.lead_time_days} days`
                : "Not provided"}
            </dd>
          </div>
        </dl>
      ) : null}
      <details className="pf-candidate-evidence">
        <summary>
          Evidence & details ·{" "}
          {c.evidence.filter((item) => item.status !== "supported").length}{" "}
          unresolved
        </summary>
        <p>{c.summary}</p>
        <p className="pf-location">
          {c.route === "make"
            ? "Manufacture to specification"
            : "Buy a supplied part"}{" "}
          · eligibility unverified
        </p>
        {sourceUrl(c.source_url) ? (
          <a
            className="pf-source-link"
            href={sourceUrl(c.source_url)}
            target="_blank"
            rel="noreferrer"
          >
            {"View supplier source"} <ExternalLink size={13} />
          </a>
        ) : (
          <small>
            {sample
              ? "Illustrative demo information · not a real supplier offer"
              : "No public source link supplied"}
          </small>
        )}
        {c.evidence.length ? (
          <ul className="pf-evidence-checks">
            {c.evidence.map((check, i) => (
              <li key={i}>
                <strong>{readable(check.requirement_key)}</strong>
                <span>
                  {readable(check.status)} — {check.note}
                  {sourceUrl(check.source_url) ? (
                    <a
                      href={sourceUrl(check.source_url)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {" "}
                      Source <ExternalLink size={12} />
                    </a>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </details>
      {
        <button
          className={selected ? "secondary" : "text-button"}
          disabled={busy || selected}
          onClick={onSelect}
        >
          {selected ? (
            <>
              <Check size={15} /> Selected for RFQ
            </>
          ) : (
            <>
              Choose this candidate <ArrowRight size={15} />
            </>
          )}
        </button>
      }
    </article>
  );
}
