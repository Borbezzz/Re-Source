import type { CaseView, Decision, RankedCandidate, Schema } from "./types.ts";

export function selectionBlock(
  view: CaseView,
  decision: Decision,
  candidate: RankedCandidate,
): string | null {
  if (
    decision.scenario_run_id !== view.scenario_run_id ||
    decision.case_id !== view.case_id
  )
    return "This option belongs to another case or run.";
  if (view.pending_change_ids.length)
    return "New evidence is being reconciled.";
  if (
    decision.decision_id !== view.current_decision_id ||
    decision.status !== "current" ||
    decision.input_revision !== view.input_revision
  )
    return "This decision has been superseded. Review the current decision.";
  if (view.stale_reasons.length)
    return "Evidence has changed. Wait for the updated decision.";
  if (candidate.eligibility !== "eligible")
    return candidate.eligibility === "pending"
      ? "Required evidence is still missing."
      : "This option does not meet the requirements.";
  if (!candidate.feasible)
    return "This option does not meet the recovery constraints.";
  return null;
}

export function submissionBlock(
  view: CaseView,
  pkg: Schema<"DocumentPackage"> | null,
): string | null {
  if (!pkg || !view.current_selection)
    return "Select an eligible option and prepare its documents.";
  if (
    view.pending_change_ids.length ||
    view.current_selection.status !== "current"
  )
    return "The selection needs review against new evidence.";
  if (
    pkg.package_id !== view.current_package_id ||
    pkg.scenario_run_id !== view.scenario_run_id ||
    pkg.selection_id !== view.current_selection.selection_id ||
    pkg.status !== "current"
  )
    return "This package is no longer current.";
  if (pkg.review_state !== "approved" || pkg.approved_hash !== pkg.package_hash)
    return "Review and approve this exact package version.";
  return null;
}

export function formatMoney(money: Schema<"Money">): string {
  // Format decimal strings without introducing floating-point monetary arithmetic.
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(money.amount);
  if (!match) return `${money.amount} ${money.currency}`;
  const integer = BigInt(match[2]).toLocaleString("en-GB");
  const decimals = match[3] ?? "00";
  const symbol = ({ GBP: "£", EUR: "€", USD: "$" } as Record<string, string>)[
    money.currency
  ];
  const amount = `${match[1]}${symbol ?? ""}${integer}${decimals === "00" ? "" : `.${decimals}`}`;
  return symbol ? amount : `${amount} ${money.currency}`;
}

export function sourceUrl(value?: string | null): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

// Structural validation is not identity validation. A supplied ref must resolve to
// the current blueprint and identify a reviewable source location or excerpt.
export function meshSourceBlock(
  job: Schema<"MeshJob">,
  blueprintId?: string,
): string | null {
  if (job.status !== "succeeded" || !job.validation?.ok)
    return "Mesh validation has not passed.";
  if (!blueprintId || !job.expected.length)
    return "The blueprint or expected part identities are missing.";
  for (const expected of job.expected) {
    const checks = job.validation.checks.filter(
      (c) =>
        c.component_id === expected.component_id &&
        c.node_name === expected.node_name,
    );
    if (checks.length !== 1 || !checks[0].ok)
      return `${expected.node_name}: a unique validated mesh is required.`;
    const ref = checks[0].source_ref;
    if (ref?.upload_id !== blueprintId)
      return `${expected.node_name}: cite the uploaded blueprint, not another source.`;
    const located =
      (ref.page != null && ref.page > 0) ||
      (ref.line != null && ref.line > 0) ||
      !!ref.element_id?.trim() ||
      !!ref.excerpt?.trim();
    if (!located)
      return `${expected.node_name}: provide a source page, line, element or excerpt for identity review.`;
  }
  return null;
}
