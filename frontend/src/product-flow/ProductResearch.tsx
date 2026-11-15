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
  comparison,
  busy,
  onAction,
  onCompare,
  onApproval,
}: {
  project: ProductProject;
  comparison: boolean;
  busy: string;
  onAction: ProjectAction;
  onCompare: () => void;
  onApproval: () => void;
}) {
  const [active, setActive] = useState<string | null>(null);
  const complete = project.research.filter(
      (r) => r.status === "complete",
    ).length,
    failed = project.research.filter((r) => r.status === "failed").length;
  const findings = candidateFindings(project);
  return (
    <section className="pf-investigation">
      <div className="pf-section-heading">
        <div>
          <h2>
            {comparison ? "Compare supplier evidence" : "Research in parallel"}
          </h2>
          <p>
            {comparison
              ? "Choose a lead for each part after reviewing its sources and unknowns."
              : `${complete} of ${project.research.length} part investigations complete${failed ? ` · ${failed} need attention` : ""}. Progress comes from the actual research tasks.`}
          </p>
        </div>
        {!comparison && project.research.some((r) => r.candidates.length) ? (
          <button className="primary" onClick={onCompare}>
            Compare candidates <ArrowRight size={16} />
          </button>
        ) : null}
        {comparison && Object.keys(project.selections).length ? (
          <button
            className="primary"
            onClick={() =>
              void onAction(
                "Preparing review package…",
                () => productApi.package(project.project_id),
                "approval",
              )
            }
          >
            Review sourcing package <ArrowRight size={16} />
          </button>
        ) : null}
      </div>
      {!project.research.length ? (
        <div className="pf-empty">
          <h3>No investigations yet.</h3>
          <p>Choose one or more parts in Assembly, then start research.</p>
        </div>
      ) : (
        <div className={comparison ? "pf-comparison" : "pf-research-layout"}>
          <div className="pf-research-jobs">
            {project.research.map((job) => {
              const part = project.parts.find((p) => p.part_id === job.part_id);
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
                      No source-backed supplier leads were found. Revise the
                      part requirements or investigate again.
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
                        comparison={comparison}
                        busy={!!busy}
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
          {!comparison ? (
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
                  locationNote="Country markers are representative, not supplier addresses. Sample suppliers use illustrative countries; public leads are plotted only when a country and source are supplied."
                />
              </Suspense>
              {!findings.length ? (
                <p className="pf-footnote">
                  No source-linked countries are available yet. Supplier names
                  and evidence stay in the list; no locations are guessed.
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
          ) : null}
        </div>
      )}
      {comparison ? (
        <p className="pf-footnote">
          Selecting a candidate prepares an RFQ. Public information and sample
          quotes do not establish supplier eligibility.
        </p>
      ) : null}
    </section>
  );
}
function Candidate({
  candidate: c,
  selected,
  active,
  comparison,
  busy,
  onFocus,
  onSelect,
}: {
  candidate: ProductCandidate;
  selected: boolean;
  active: boolean;
  comparison: boolean;
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
      {comparison ? (
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
      ) : null}
    </article>
  );
}
