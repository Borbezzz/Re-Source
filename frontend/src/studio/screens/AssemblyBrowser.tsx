import { useId, useState } from "react";
import { ChevronDown, X } from "lucide-react";
import type { AssemblyItem } from "../data/assembly.ts";

type BrowserProps = {
  items: AssemblyItem[];
  selected: string | null;
  onSelect: (item: AssemblyItem) => void;
  onHover: (item: AssemblyItem | null) => void;
};

function PartRow({ item, depth, selected, onSelect, onHover }: Omit<BrowserProps, "items"> & { item: AssemblyItem; depth: number }) {
  const [open, setOpen] = useState(depth === 0 && item.assemblyId === "fan");
  const childrenId = useId();
  const branch = item.children.length > 0;
  return (
    <li className="rs-part-node" data-part-id={item.id}>
      <div className={`rs-part-row${selected === item.id ? " is-selected" : ""}`}
        style={{ paddingLeft: 8 + depth * 12 }}
        onPointerEnter={e => { if (e.pointerType !== "touch") onHover(item); }}
        onPointerLeave={() => onHover(null)}
        onFocus={() => onHover(item)}
        onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) onHover(null); }}>
        {branch ? (
          <button type="button" className="rs-part-toggle" aria-label={`${open ? "Collapse" : "Expand"} ${item.name}`}
            aria-expanded={open} aria-controls={childrenId} onClick={() => setOpen(value => !value)}>
            <ChevronDown size={14} aria-hidden="true" />
          </button>
        ) : <span className="rs-part-leaf" aria-hidden="true" />}
        <button type="button" className="rs-part-select" aria-pressed={selected === item.id} onClick={() => { onHover(null); onSelect(item); }}>
          <span>{item.name}</span>
          {branch ? <span className="rs-part-count">{item.pieceCount}</span> : null}
        </button>
      </div>
      {branch && open ? (
        <ul id={childrenId} className="rs-part-children">
          {item.children.map(child => <PartRow key={child.id} item={child} depth={depth + 1} selected={selected} onSelect={onSelect} onHover={onHover} />)}
        </ul>
      ) : null}
    </li>
  );
}

export function AssemblyBrowser({ items, selected, onSelect, onHover }: BrowserProps) {
  const [open, setOpen] = useState(true);
  return (
    <aside className={`rs-components rs-parts-browser${open ? "" : " is-collapsed"}`} aria-label="Assembly parts" style={{ bottom: open ? 24 : "auto" }}
      onKeyDown={e => { if (e.key === "Escape") { onHover(null); (e.target as HTMLElement).blur(); } }}>
      <button type="button" className="rs-components-head" aria-expanded={open} onClick={() => { setOpen(v => !v); onHover(null); }}>
        Parts <ChevronDown size={18} aria-hidden="true" />
      </button>
      {open ? <>
        <p className="rs-parts-hint">Hover to highlight. Expand a group to inspect each piece.</p>
        <ul className="rs-part-tree" onPointerLeave={() => onHover(null)}>
          {items.map(item => <PartRow key={item.id} item={item} depth={0} selected={selected} onSelect={onSelect} onHover={onHover} />)}
        </ul>
      </> : null}
    </aside>
  );
}

export function InspectionCard({ item, onClose }: { item: AssemblyItem; onClose: () => void }) {
  return (
    <section className="rs-context rs-panel rs-inspection-card" aria-label={`${item.name} inspection`}>
      <div className="rs-inspection-heading"><h2 className="rs-anchor-title">{item.name}</h2>
        <button type="button" className="rs-btn rs-btn-ghost rs-btn-sm" onClick={onClose} aria-label="Clear selection"><X size={16} /></button>
      </div>
      <p className="rs-small">{item.pieceCount === 1 ? "1 model piece" : `${item.pieceCount.toLocaleString()} model pieces`} · prepared assembly</p>
      <p className="rs-small rs-inspection-note">{item.children.length
        ? "Expand this group and select a part to replace it or change its supplier."
        : "This geometry has no sourcing specification in the uploaded package. A part identity and requirements are needed before supplier research."}</p>
    </section>
  );
}
