export type DemoScreen =
  "sources" | "assembly" | "investigations" | "suppliers" | "documents";

export interface DemoSession {
  runId: string;
  componentId: string;
  partId?: string;
  blueprintId?: string;
  requirementsId?: string;
  draftId?: string;
}

const key = "resource:prepared-demo:v1";

export function readDemoSession(): DemoSession | null {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(key) ?? "null");
    if (
      value &&
      typeof value === "object" &&
      "runId" in value &&
      "componentId" in value &&
      typeof value.runId === "string" &&
      typeof value.componentId === "string"
    ) {
      const restored: DemoSession = {
        runId: value.runId,
        componentId: value.componentId,
      };
      for (const field of [
        "partId",
        "blueprintId",
        "requirementsId",
        "draftId",
      ] as const) {
        const optionalValue: unknown = Reflect.get(value, field);
        if (typeof optionalValue === "string") restored[field] = optionalValue;
      }
      return restored;
    }
  } catch {
    /* Storage is optional; the current visit can still use the guide. */
  }
  return null;
}

export function saveDemoSession(value: DemoSession | null) {
  try {
    if (value) sessionStorage.setItem(key, JSON.stringify(value));
    else sessionStorage.removeItem(key);
  } catch {
    /* A storage restriction must not block the real workflow. */
  }
}

// Use the same run-scoped intake record as the normal upload screen. The guide
// only supplies files; review, corrections and confirmation stay in Intake.
export function saveDemoIntake(value: DemoSession) {
  sessionStorage.setItem(
    `resource:intake:v1:${value.runId}`,
    JSON.stringify({
      componentId: value.componentId,
      blueprintId: value.blueprintId,
      requirementsId: value.requirementsId,
      draftId: value.draftId,
    }),
  );
}

export const DEMO_BLUEPRINT = `SYNTHETIC PREPARED DEMO — NOT AN ENGINEERING DRAWING
Assembly: RS-TF2 representative turbofan
Configuration: RS-TF2-CFG-A

Selectable components in the prepared model:
7. Combustor fuel nozzle — RS-FN-1001, revision D
12. Nozzle guide vane segment — RS-NGV-2040
HP. High-pressure bleed duct — RS-BD-3110

Fuel nozzle sample dimension: 12 mm (invented test value).
This text exercises source upload and traceability. It does not define the
prepared model's shape, dimensions, performance or engineering compatibility.
The model is separately prepared. Blueprint-to-mesh generation needs a provider.
`;

export const DEMO_REQUIREMENTS = `SYNTHETIC PREPARED DEMO — NOT FOR PROCUREMENT OR ENGINEERING USE
PART_NUMBER: RS-FN-1001
REVISION: D
DESCRIPTION: Prepared-demo fuel nozzle specification; all data is synthetic.
KEY_DIMENSIONS: 12 mm (invented test value; requires manual evidence review)
DRAWING_UNITS: mm

Only confirmed part identity and revision currently enter automated sourcing
checks. Uploaded dimensions, materials, tolerances and certifications need manual
evidence review; the prepared mesh does not prove these requirements.
`;

export function sampleFile(kind: "blueprint" | "requirements") {
  return new File(
    [kind === "blueprint" ? DEMO_BLUEPRINT : DEMO_REQUIREMENTS],
    kind === "blueprint"
      ? "SYNTHETIC-DEMO-blueprint.txt"
      : "SYNTHETIC-DEMO-fuel-nozzle-specification.txt",
    { type: "text/plain" },
  );
}
