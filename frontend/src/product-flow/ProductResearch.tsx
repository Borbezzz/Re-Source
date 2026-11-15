import { lazy, Suspense, useState } from "react";
import { ArrowRight, Check, ExternalLink } from "lucide-react";
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
      <div className="pf-research-layout">
        <div className="pf-research-jobs">
          {project.research.map((job) => {
            const part = project.parts.find(
              (value) => value.part_id === job.part_id,
            );
            return (
              <section className="pf-research-job" key={job.job_id}>
                <div className="pf-job-heading">
                  <div>
                    <h3>{part?.name ?? job.part_id}</h3>
                    <p>{readable(job.stage)}</p>
                  </div>
                  <span className={`pf-job-status pf-job-${job.status}`}>
                    {readable(job.status)}
                  </span>
                </div>
                {job.summary ? <p>{job.summary}</p> : null}
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
                  {job.candidates.map((candidate) => (
                    <Candidate
                      key={candidate.candidate_id}
                      candidate={candidate}
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
        </div>
        <aside className="pf-research-map">
          <Suspense
            fallback={
              <div className="pf-empty">Opening sourced locations…</div>
            }
          >
            <ResearchGlobe
              findings={findings}
              selected={active}
              onSelect={setActive}
              locationLabel="reported countries"
              locationNote="Country markers are representative, not supplier addresses. Sample suppliers use illustrative countries; public leads require a country and source."
            />
          </Suspense>
          {!findings.length ? (
            <p className="pf-footnote">
              No source-linked countries are available yet. All supplier
              evidence remains in the list.
            </p>
          ) : null}
          <details className="pf-activity">
            <summary>
              Research activity · {project.events.length} events
            </summary>
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
        </aside>
      </div>
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
  selected,
  active,
  busy,
  onFocus,
  onSelect,
}: {
  candidate: ProductCandidate;
  selected: boolean;
  active: boolean;
  busy: boolean;
  onFocus: () => void;
  onSelect: () => void;
}) {
  const sample = c.data_origin === "synthetic_demo";
  return (
    <article
      className={`pf-candidate ${active ? "pf-candidate-active" : ""} ${selected ? "pf-candidate-selected" : ""}`}
      onFocus={onFocus}
    >
      <div className="pf-candidate-heading">
        <h4>{c.supplier_name}</h4>
        <span>{sample ? "Sample quote" : "Public supplier lead"}</span>
      </div>
      <p>{c.summary}</p>
      <p className="pf-location">
        {c.route === "make"
          ? "Manufacture to specification"
          : "Buy a supplied part"}{" "}
        · eligibility unverified
      </p>
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
      {c.country ? (
        <p className="pf-location">
          {c.country} ·{" "}
          {sample
            ? "illustrative demo location"
            : "reported country, not a verified site"}
        </p>
      ) : null}
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
        <details className="pf-candidate-evidence">
          <summary>
            Requirements & evidence ·{" "}
            {c.evidence.filter((item) => item.status !== "supported").length}{" "}
            unresolved
          </summary>
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
        </details>
      ) : null}
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
