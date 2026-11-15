/**
 * Fictional supplier-site evidence fixtures for the prepared Mechanica demo.
 * Keyed by the backend sample-offer candidate_id (data/demo-products/turbofan.json),
 * which supplies supplier name, price and dispatch lead time. Coordinates are
 * real city locations of the *supplying site* (not a headquarters); company
 * names, stock, documents and quotes are invented demo data.
 */
export type Evidence = "provided" | "missing";
export interface SiteFixture {
  city: string;
  countryCode: string;
  lat: number;
  lon: number;
  siteType: string;
  offeredPartNumber?: string; // defaults to the required part number
  offeredRevision?: string; // defaults to the required revision
  offeredCondition?: string; // defaults to "New"
  applicability: Evidence;
  traceability: Evidence;
  siteEvidence: Evidence;
  stock: number | null;
  transitDays: number;
  sourceLabel: string;
}

export const DESTINATION = {
  name: "Filton, Bristol",
  short: "Bristol",
  lat: 51.519,
  lon: -2.575,
  site: "Demo Aero Maintenance — Hangar 3, Filton, Bristol BS34",
};

const S = (f: SiteFixture) => f;
const derby = { city: "Derby", countryCode: "GB", lat: 52.9225, lon: -1.4746 };
const toulouse = { city: "Toulouse", countryCode: "FR", lat: 43.6045, lon: 1.444 };
const hamburg = { city: "Hamburg", countryCode: "DE", lat: 53.5511, lon: 9.9937 };
const glasgow = { city: "Glasgow", countryCode: "GB", lat: 55.8642, lon: -4.2518 };
const kongsberg = { city: "Kongsberg", countryCode: "NO", lat: 59.6689, lon: 9.6502 };
const lyon = { city: "Lyon", countryCode: "FR", lat: 45.764, lon: 4.8357 };
const munich = { city: "Munich", countryCode: "DE", lat: 48.1351, lon: 11.582 };
const getafe = { city: "Getafe", countryCode: "ES", lat: 40.3057, lon: -3.7329 };
const turin = { city: "Turin", countryCode: "IT", lat: 45.0703, lon: 7.6869 };
const shannon = { city: "Shannon", countryCode: "IE", lat: 52.7038, lon: -8.8645 };
const gdansk = { city: "Gdańsk", countryCode: "PL", lat: 54.352, lon: 18.6466 };
const brno = { city: "Brno", countryCode: "CZ", lat: 49.1951, lon: 16.6068 };

const ok = { applicability: "provided", traceability: "provided", siteEvidence: "provided" } as const;

export const SITES: Record<string, SiteFixture> = {
  // Front fan blade 01 · RS-DEMO-FB-001 Rev B
  "rs-tf-fan-blade-site-01": S({ ...derby, ...ok, siteType: "Stockist warehouse", stock: 2, transitDays: 1, sourceLabel: "Supplier stock list (demo)" }),
  "rs-tf-fan-blade-site-02": S({ ...toulouse, ...ok, siteType: "Production & dispatch", stock: 1, transitDays: 3, sourceLabel: "Capability statement (demo)" }),
  "rs-tf-fan-blade-site-03": S({ ...hamburg, ...ok, siteType: "Distribution centre", stock: 3, transitDays: 3, sourceLabel: "Distributor catalogue (demo)" }),
  "rs-tf-fan-blade-site-04": S({ ...glasgow, ...ok, siteEvidence: "missing", siteType: "Machining site", stock: 1, transitDays: 1, sourceLabel: "Trade directory listing (demo)" }),
  "rs-tf-fan-blade-site-05": S({ ...kongsberg, ...ok, siteType: "Production site", stock: null, transitDays: 4, sourceLabel: "Website product page (demo)" }),
  "rs-tf-fan-blade-site-06": S({ ...lyon, ...ok, offeredRevision: "A", siteType: "Production site", stock: 4, transitDays: 3, sourceLabel: "Quoted listing (demo)" }),
  "rs-tf-fan-blade-site-07": S({ ...munich, ...ok, siteType: "Build-to-print shop", stock: null, transitDays: 4, sourceLabel: "Capability statement (demo)" }),
  "rs-tf-fan-blade-site-08": S({ ...getafe, ...ok, traceability: "missing", siteType: "Stockist warehouse", stock: 1, transitDays: 4, sourceLabel: "Stock list (demo)" }),
  "rs-tf-fan-blade-site-09": S({ ...turin, ...ok, applicability: "missing", siteType: "Production site", stock: 2, transitDays: 4, sourceLabel: "Website product page (demo)" }),
  "rs-tf-fan-blade-site-10": S({ ...shannon, ...ok, offeredCondition: "Overhauled", siteType: "Overhaul & exchange", stock: 6, transitDays: 2, sourceLabel: "Exchange-pool listing (demo)" }),
  "rs-tf-fan-blade-site-11": S({ ...gdansk, ...ok, offeredRevision: "C", siteType: "Production site", stock: 2, transitDays: 4, sourceLabel: "Quoted listing (demo)" }),
  "rs-tf-fan-blade-site-12": S({ ...brno, ...ok, siteType: "Build-to-print shop", stock: null, transitDays: 4, sourceLabel: "Capability statement (demo)" }),
  // Fuel injector 01 · RS-DEMO-FI-001 Rev C
  "rs-tf-fuel-injector-site-01": S({ ...derby, ...ok, siteType: "Stockist warehouse", stock: 4, transitDays: 1, sourceLabel: "Supplier stock list (demo)" }),
  "rs-tf-fuel-injector-site-02": S({ ...toulouse, ...ok, siteType: "Production & dispatch", stock: 2, transitDays: 3, sourceLabel: "Capability statement (demo)" }),
  "rs-tf-fuel-injector-site-03": S({ ...hamburg, ...ok, traceability: "missing", siteType: "Distribution centre", stock: 3, transitDays: 3, sourceLabel: "Distributor catalogue (demo)" }),
  "rs-tf-fuel-injector-site-04": S({ ...turin, ...ok, siteType: "Build-to-print shop", stock: null, transitDays: 4, sourceLabel: "Capability statement (demo)" }),
  "rs-tf-fuel-injector-site-05": S({ ...getafe, ...ok, offeredRevision: "B", siteType: "Stockist warehouse", stock: 5, transitDays: 4, sourceLabel: "Stock list (demo)" }),
  // Core exhaust nozzle assembly · RS-DEMO-NZ-001 Rev A
  "rs-tf-core-nozzle-site-01": S({ ...toulouse, ...ok, siteType: "Production & dispatch", stock: 1, transitDays: 3, sourceLabel: "Capability statement (demo)" }),
  "rs-tf-core-nozzle-site-02": S({ ...hamburg, ...ok, siteType: "Distribution centre", stock: 1, transitDays: 3, sourceLabel: "Distributor catalogue (demo)" }),
  "rs-tf-core-nozzle-site-03": S({ ...glasgow, ...ok, siteType: "Fabrication site", stock: null, transitDays: 1, sourceLabel: "Trade directory listing (demo)" }),
  "rs-tf-core-nozzle-site-04": S({ ...gdansk, ...ok, siteEvidence: "missing", siteType: "Production site", stock: 1, transitDays: 4, sourceLabel: "Quoted listing (demo)" }),
};

/** Simulated monitoring signal used in the demo disruption step. */
export const DISRUPTION = {
  id: "SIG-DEMO-DERBY-HOLD",
  source: "Supplier notice · simulated",
  title: "Dispatch hold at Derby stockist",
  detail: "Furnace outage stops heat-treatment release. Earliest dispatch moves back 13 days.",
  city: "Derby",
  extraDispatchDays: 13,
  affects: (candidateId: string) => candidateId.endsWith("-site-01") && SITES[candidateId]?.city === "Derby",
  rerun: ["availability", "arrival"] as const,
};
