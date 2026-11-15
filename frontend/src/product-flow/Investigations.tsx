import { useEffect, useState } from "react";
import { ArrowRight, Plus, RefreshCw } from "lucide-react";
import { productApi } from "./client.ts";
import type { ProductProjectSummary } from "./types.ts";

export function investigationState(project: ProductProjectSummary): string {
  if (project.active_research_count)
    return `Researching ${project.active_research_count} ${project.active_research_count === 1 ? "part" : "parts"}`;
  if (project.status === "extracting") return "Reading documents";
  if (project.package_status === "simulated") return "Demo complete";
  if (project.package_status === "approved") return "Ready to simulate";
  if (project.package_status === "draft") return "Review RFQ";
  if (project.failed_research_count) return "Research needs attention";
  if (project.completed_research_count) return "Review suppliers";
  if (project.part_count && project.confirmed_part_count === project.part_count)
    return "Choose parts to research";
  if (project.part_count) return "Review extracted parts";
  return "Add documents or parts";
}

const updatedDate = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function Investigations() {
  const [projects, setProjects] = useState<ProductProjectSummary[] | null>(
    null,
  );
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let inFlight = false;
    const load = async () => {
      if (inFlight || controller.signal.aborted) return;
      inFlight = true;
      try {
        const result = await productApi.projects(controller.signal);
        if (controller.signal.aborted) return;
        setProjects(result.projects);
        setError("");
      } catch (cause) {
        if (!controller.signal.aborted)
          setError(
            cause instanceof Error
              ? cause.message
              : "Your investigations could not be loaded.",
          );
      } finally {
        inFlight = false;
        clearTimeout(timer);
        if (!controller.signal.aborted)
          timer = setTimeout(() => {
            if (document.visibilityState === "visible") void load();
          }, 8000);
      }
    };
    const resume = () => {
      if (document.visibilityState === "visible") {
        clearTimeout(timer);
        void load();
      }
    };
    void load();
    document.addEventListener("visibilitychange", resume);
    return () => {
      controller.abort();
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [refresh]);

  return (
    <div className="investigations-page">
      <div className="investigations-heading">
        <div>
          <h1>Investigations</h1>
          <p>
            Pick up where you left off. Research keeps running while you’re
            away.
          </p>
        </div>
        <a className="primary" href="#new">
          <Plus size={17} aria-hidden="true" /> New investigation
        </a>
      </div>
      {error && (
        <div className="investigations-error" role="alert">
          <p>
            {projects
              ? "We couldn’t refresh your investigations. The last saved list is shown."
              : error}
          </p>
          <button
            className="secondary"
            onClick={() => setRefresh((value) => value + 1)}
          >
            <RefreshCw size={15} aria-hidden="true" /> Try again
          </button>
        </div>
      )}
      {!projects && !error && (
        <div className="workspace-loading" role="status">
          Loading your investigations…
        </div>
      )}
      {projects?.length === 0 && (
        <section className="investigations-empty">
          <h2>Your investigations will appear here</h2>
          <p>
            Start with your own design package or a prepared demo. Your
            documents, research and supplier choices stay together.
          </p>
          <a className="text-button" href="#new">
            Start your first investigation{" "}
            <ArrowRight size={17} aria-hidden="true" />
          </a>
        </section>
      )}
      {Boolean(projects?.length) && (
        <>
          <div className="investigations-list-label">
            <span>Saved investigations</span>
            <span>
              {projects!.length === 100
                ? "Most recent 100"
                : `${projects!.length} saved`}
            </span>
          </div>
          <ul className="investigations-list">
            {projects!.map((project) => (
              <li key={project.project_id}>
                <a
                  className="investigation-row"
                  href={`#project/${project.project_id}`}
                >
                  <div className="investigation-identity">
                    <h2>{project.name}</h2>
                    <p>
                      {project.demo_id
                        ? "Prepared demo"
                        : "Your design package"}{" "}
                      · {project.part_count}{" "}
                      {project.part_count === 1 ? "part" : "parts"}
                    </p>
                  </div>
                  <div className="investigation-progress">
                    <span
                      className={
                        project.active_research_count ? "is-running" : ""
                      }
                    >
                      {investigationState(project)}
                    </span>
                    <time dateTime={project.updated_at}>
                      Updated {updatedDate.format(new Date(project.updated_at))}
                    </time>
                  </div>
                  <span className="investigation-resume">
                    {project.package_status === "simulated"
                      ? "View"
                      : "Continue"}
                    <ArrowRight size={18} aria-hidden="true" />
                  </span>
                </a>
              </li>
            ))}
          </ul>
          <p className="investigations-privacy">
            Saved for this browser. Open any investigation to see its documents,
            progress and results.
          </p>
        </>
      )}
    </div>
  );
}
