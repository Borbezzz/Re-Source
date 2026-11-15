import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Logo } from "./studio/brand/Logo.tsx";
import { Investigations } from "./product-flow/Investigations.tsx";
import { readRoute, routeHash, type AppRoute } from "./navigation.ts";
import "./workspace.css";

const ProductFlow = lazy(() =>
  import("./product-flow/ProductFlow.tsx").then((m) => ({
    default: m.ProductFlow,
  })),
);
const LegacyEngineApp = lazy(() => import("./LegacyEngineApp.tsx"));
const Studio = lazy(() =>
  import("./studio/Studio.tsx").then((m) => ({ default: m.Studio })),
);
const QuotePage = lazy(() =>
  import("./studio/quotes/QuotePage.tsx").then((m) => ({ default: m.QuotePage })),
);

export default function App() {
  const [route, setRoute] = useState(() => readRoute(location.hash));
  const [visit, setVisit] = useState(0);
  const sourceDirty = useRef(false);
  const historyIndex = useRef<number>(history.state?.resourceNavigation ?? 0);
  useEffect(() => {
    history.replaceState(
      { ...history.state, resourceNavigation: historyIndex.current },
      "",
    );
    let restoring = false;
    const changed = () => {
      if (restoring) {
        restoring = false;
        return;
      }
      if (
        sourceDirty.current &&
        !window.confirm(
          "Leave this investigation? Your unsaved part edits will be lost.",
        )
      ) {
        // Restore the original history position; never overwrite the page the
        // user was going back to when they choose to keep their draft.
        const destination = history.state?.resourceNavigation;
        restoring = true;
        history.go(
          typeof destination === "number"
            ? historyIndex.current - destination
            : -1,
        );
        return;
      }
      const destination = history.state?.resourceNavigation;
      historyIndex.current =
        typeof destination === "number"
          ? destination
          : historyIndex.current + 1;
      history.replaceState(
        { ...history.state, resourceNavigation: historyIndex.current },
        "",
      );
      sourceDirty.current = false;
      setRoute(readRoute(location.hash));
      setVisit((value) => value + 1);
      if (location.hash !== "#prepared-assembly") {
        window.scrollTo(0, 0);
        requestAnimationFrame(() =>
          document
            .getElementById("main-content")
            ?.focus({ preventScroll: true }),
        );
      }
    };
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  const navigate = (next: AppRoute) => {
    const hash = routeHash(next);
    if (location.hash === hash) return;
    location.hash = hash;
  };
  const openedProject = (id: string) => {
    history.replaceState(history.state, "", routeHash({ page: "project", id }));
    setRoute({ page: "project", id });
  };

  if (route.page === "home")
    return (
      <Suspense fallback={<div className="rs-boot" role="status" />}>
        <Studio />
      </Suspense>
    );
  if (route.page === "quotes")
    return (
      <Suspense fallback={<div className="workspace-loading" role="status">Opening supplier quotes…</div>}>
        <QuotePage key={route.id} projectId={route.id} />
      </Suspense>
    );

  return (
    <>
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to content
      </a>
      <header className="global-header app-header">
        <a className="wordmark" href="#home" aria-label="Re::Source home" style={{ textDecoration: "none" }}>
          <Logo size={26} />
        </a>
        <nav aria-label="Main navigation">
          <a
            href="#home"
          >
            Studio
          </a>
          <a
            href="#investigations"
            aria-current={
              route.page === "investigations" ||
              route.page === "project" ||
              route.page === "legacy"
                ? "page"
                : undefined
            }
          >
            Investigations
          </a>
          <a
            href="#new"
            aria-current={route.page === "new" ? "page" : undefined}
          >
            New investigation
          </a>
        </nav>
      </header>
      {(
        <main id="main-content" tabIndex={-1} className="workspace-main">
          {route.page === "investigations" ? (
            <Investigations />
          ) : route.page === "legacy" ? (
            <Suspense
              fallback={
                <div className="workspace-loading" role="status">
                  Opening saved engine workspace…
                </div>
              }
            >
              <LegacyEngineApp key={visit} />
            </Suspense>
          ) : (
            <Suspense
              fallback={
                <div className="workspace-loading" role="status">
                  Opening investigation…
                </div>
              }
            >
              <ProductFlow
                key={visit}
                entry={
                  route.page === "project"
                    ? `project:${route.id}`
                    : route.upload
                      ? "upload"
                      : "gallery"
                }
                onProjectOpened={openedProject}
                onDirtyChange={(dirty) => {
                  sourceDirty.current = dirty;
                }}
                onNew={() => navigate({ page: "new" })}
              />
            </Suspense>
          )}
        </main>
      )}
    </>
  );
}
