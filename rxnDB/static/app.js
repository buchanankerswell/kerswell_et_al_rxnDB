/* rxnDB search page logic. Same endpoints serve browsers and agents. */

const query_input = document.getElementById("query");
const type_select = document.getElementById("reaction_type");
const count_el = document.getElementById("count");
const plot_svg = document.getElementById("plot");
const plot_tip = document.getElementById("plot_tip");
const plot_note = document.getElementById("plot_note");

function read_state() {
  const params = new URLSearchParams(location.search);
  return { query: params.get("query") || "", reaction_type: params.get("reaction_type") || "", selected: params.get("selected") || "" };
}

function write_state(state) {
  const params = new URLSearchParams();
  if (state.query) params.set("query", state.query);
  if (state.reaction_type) params.set("reaction_type", state.reaction_type);
  if (state.selected) params.set("selected", state.selected);
  history.replaceState(null, "", "?" + params.toString());
}

function escape_html(text) {
  return String(text).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}

function symbols(reaction) {
  return [...reaction.reactants, ...reaction.products].map(p => p.mineral_symbol).join(" + ");
}

function suspect(reaction) {
  return reaction.extensions && reaction.extensions.verification_status === "suspect";
}

/* Sample a stored P(T) polynomial, breaking the line outside valid ranges. */
function sample_curve(boundary) {
  const low = boundary.valid_temperature_min_celsius ?? 400;
  const high = boundary.valid_temperature_max_celsius ?? 1800;
  const floor = Math.max(boundary.valid_pressure_min_gigapascal ?? 0, 0);
  const ceiling = boundary.valid_pressure_max_gigapascal ?? null;
  return Array.from({ length: 40 }, (_, i) => {
    const t = low + (high - low) * i / 39;
    const p = boundary.pressure_intercept_gigapascal
      + boundary.pressure_slope_gigapascal_per_celsius * t
      + boundary.pressure_curvature_gigapascal_per_celsius_squared * t * t
      + boundary.pressure_cubic_gigapascal_per_celsius_cubed * t * t * t;
    return { t, p: (p < floor || (ceiling !== null && ceiling !== undefined && p > ceiling)) ? null : p };
  });
}

let selected = "";
let refresh_seq = 0;
let plot_seq = 0;
let list_controller = null;
let debounce_timer = null;
let plot_timer = null;
let plot_pending = null;
let plot_ready = false;
const analysis_cache = new Map();
let last_records = [];
let plot_owners = [];

const DIM_OPACITY = 0.5;
let hovered = null;
const PLOT_LIMIT = 200;

const SVG_W = 720, SVG_H = 440;
const PAD = { left: 52, right: 14, top: 10, bottom: 46 };

function nice_step(span, target = 4) {
  const raw = span / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7.5 ? 5 : 10;
  return step * mag;
}

function ticks(min, max) {
  const span = max - min || 1;
  const step = nice_step(span);
  const out = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(9));
  return out;
}

function format_tick(v, step) {
  if (step >= 1) return String(Math.round(v));
  const decimals = Math.min(6, Math.max(0, -Math.floor(Math.log10(step))));
  return v.toFixed(decimals).replace(/\.?0+$/, "");
}

function star_points(cx, cy, r) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const rad = i % 2 === 0 ? r : r * 0.45;
    const a = -Math.PI / 2 + i * Math.PI / 5;
    pts.push((cx + rad * Math.cos(a)).toFixed(1) + "," + (cy + rad * Math.sin(a)).toFixed(1));
  }
  return pts.join(" ");
}

function apply_spotlight() {
  if (!plot_svg) return;
  const groups = plot_svg.querySelectorAll("g.series");
  if (groups.length !== plot_owners.length) return;
  const focus = hovered || selected || null;
  if (focus !== null && !plot_owners.includes(focus)) return;
  groups.forEach(g => {
    g.setAttribute("opacity", (focus !== null && g.dataset.owner === focus) ? "1" : String(DIM_OPACITY));
  });
}

function emphasize(identifier) {
  hovered = identifier;
  apply_spotlight();
}

function clear_emphasis() {
  hovered = null;
  apply_spotlight();
}

async function analysis_for(identifier) {
  if (analysis_cache.has(identifier)) return analysis_cache.get(identifier);
  const [fit, design] = await Promise.all([
    (await fetch("/fit/boundary", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reaction_identifier: identifier }),
    })).json(),
    (await fetch("/design/next-point", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reaction_identifier: identifier, candidate_count: 20 }),
    })).json(),
  ]);
  const result = { fit, design };
  analysis_cache.set(identifier, result);
  return result;
}

async function refresh() {
  const seq = ++refresh_seq;
  const state = { query: query_input.value, reaction_type: type_select.value, selected };
  write_state(state);
  if (list_controller) list_controller.abort();
  list_controller = new AbortController();
  count_el.textContent = "Searching…";
  const params = new URLSearchParams();
  if (state.query) params.set("query", state.query);
  if (state.reaction_type) params.set("reaction_type", state.reaction_type);
  let records;
  try {
    records = await (await fetch("/reactions?" + params.toString(), { signal: list_controller.signal })).json();
  } catch (error) {
    if (error.name === "AbortError") return;
    throw error;
  }
  if (seq !== refresh_seq) return;
  last_records = records;

  const total = records.length;
  count_el.textContent = total === 0 ? "No reactions match."
    : `${total} reaction${total === 1 ? "" : "s"}`;

  document.getElementById("reaction_list").innerHTML = records.map(r =>
    `<li><a href="#" data-id="${escape_html(r.reaction_identifier)}" aria-current="${r.reaction_identifier === selected}">` +
    `<span class="row-main"><span class="id">${escape_html(r.reaction_identifier)}</span>` +
    `${suspect(r) ? `<span class="pill">review</span>` : ""}</span>` +
    `<span class="sym">${escape_html(symbols(r))}</span></a></li>`).join("");
  document.querySelectorAll("#reaction_list a").forEach(link =>
    link.addEventListener("click", event => { event.preventDefault(); select(link.dataset.id); }));

  schedule_plot(records);

  const rows = records.flatMap(r =>
    r.observations.map(o => `<tr><td>${escape_html(r.reaction_identifier)}</td><td class="num">${o.temperature_celsius}</td><td class="num">${o.pressure_gigapascal.toFixed(2)}</td><td>${escape_html(o.experimental_outcome)}</td><td>${escape_html(r.source.short_citation)}</td></tr>`)
  );
  document.querySelector("#table tbody").innerHTML = rows.join("");
}

// The list and table redraw cheaply on every keystroke, but a full plot
// redraw is slow with hundreds of series, so filter changes only schedule
// the plot trailing-edge: typing stays instant and the plot catches up.
function schedule_plot(records) {
  if (!plot_ready) {
    plot_ready = true;
    render_plot(records);
    return;
  }
  plot_pending = records;
  clearTimeout(plot_timer);
  plot_timer = setTimeout(() => {
    const pending = plot_pending;
    plot_pending = null;
    render_plot(pending);
  }, 250);
}

// Toggling a selection redraws only the highlight and the plot, reusing the
// fetched records, so the list and table never flash.
async function select(identifier) {
  selected = (selected === identifier) ? "" : identifier;
  write_state({ query: query_input.value, reaction_type: type_select.value, selected });
  document.querySelectorAll("#reaction_list a").forEach(other => {
    other.setAttribute("aria-current", String(other.dataset.id === selected));
  });
  clearTimeout(plot_timer);
  plot_pending = null;
  await render_plot(last_records);
}

async function render_plot(records) {
  const seq = ++plot_seq;
  // The plot covers the first PLOT_LIMIT matches (ranked most relevant
  // first) so redraws stay instant; the list and table below stay complete.
  const plotted = records.slice(0, PLOT_LIMIT);

  if (records.length > plotted.length) {
    plot_note.hidden = false;
    plot_note.textContent = `Plot shows first ${plotted.length} of ${records.length} — narrow the query for more.`;
  } else {
    plot_note.hidden = true;
    plot_note.textContent = "";
  }

  const points = [];
  plotted.forEach(r => {
    r.observations.forEach(o => points.push({ t: o.temperature_celsius, p: o.pressure_gigapascal }));
    r.interpreted_boundaries.forEach(b => sample_curve(b).forEach(s => {
      if (s.p !== null) points.push({ t: s.t, p: s.p });
    }));
  });

  if (points.length === 0) {
    plot_owners = [];
    plot_svg.innerHTML = `<text x="${SVG_W / 2}" y="${SVG_H / 2}" text-anchor="middle" class="plot-empty">No points in this filter set.</text>`;
    plot_tip.hidden = true;
    return;
  }

  let tmin = Math.min(...points.map(d => d.t));
  let tmax = Math.max(...points.map(d => d.t));
  let pmin = Math.min(...points.map(d => d.p));
  let pmax = Math.max(...points.map(d => d.p));
  if (tmax - tmin < 1e-9) { tmin -= 1; tmax += 1; }
  if (pmax - pmin < 1e-9) { pmin -= 0.1; pmax += 0.1; }
  const tpad = (tmax - tmin) * 0.04, ppad = (pmax - pmin) * 0.06;
  tmin -= tpad; tmax += tpad; pmin -= ppad; pmax += ppad;

  const PW = SVG_W - PAD.left - PAD.right;
  const PH = SVG_H - PAD.top - PAD.bottom;
  const X = t => PAD.left + (t - tmin) / (tmax - tmin) * PW;
  const Y = p => PAD.top + (1 - (p - pmin) / (pmax - pmin)) * PH;

  const yticks = ticks(pmin, pmax);
  const xticks = ticks(tmin, tmax);
  const ystep = yticks.length > 1 ? yticks[1] - yticks[0] : 1;
  const xstep = xticks.length > 1 ? xticks[1] - xticks[0] : 1;

  let svg = `<defs><clipPath id="plot_clip"><rect x="${PAD.left}" y="${PAD.top}" width="${PW}" height="${PH}"/></clipPath></defs>`;

  yticks.forEach((v, i) => {
    const yy = Y(v).toFixed(1);
    const solid = i === 0;
    svg += `<line x1="${PAD.left}" y1="${yy}" x2="${SVG_W - PAD.right}" y2="${yy}" class="${solid ? "grid-solid" : "grid-line"}"/>`;
    svg += `<text x="${PAD.left - 8}" y="${yy}" text-anchor="end" dominant-baseline="central" class="tick">${escape_html(format_tick(v, ystep))}</text>`;
  });
  xticks.forEach(v => {
    svg += `<text x="${X(v).toFixed(1)}" y="${PAD.top + PH + 18}" text-anchor="middle" class="tick">${escape_html(format_tick(v, xstep))}</text>`;
  });
  svg += `<text x="${PAD.left + PW / 2}" y="${SVG_H - 4}" text-anchor="middle" class="axis-title">Temperature (°C)</text>`;
  svg += `<text x="12" y="${PAD.top + PH / 2}" text-anchor="middle" transform="rotate(-90 12 ${PAD.top + PH / 2})" class="axis-title">Pressure (GPa)</text>`;

  svg += `<g clip-path="url(#plot_clip)">`;
  plot_owners = [];
  plotted.forEach(r => {
    const id = escape_html(r.reaction_identifier);
    plot_owners.push(r.reaction_identifier);
    let g = `<g class="series" data-owner="${id}">`;
    r.observations.forEach(o => {
      const cx = X(o.temperature_celsius).toFixed(1), cy = Y(o.pressure_gigapascal).toFixed(1);
      const tu = o.temperature_uncertainty_celsius || 0;
      const pu = o.pressure_uncertainty_gigapascal || 0;
      if (tu > 0) {
        g += `<line x1="${X(o.temperature_celsius - tu).toFixed(1)}" y1="${cy}" x2="${X(o.temperature_celsius + tu).toFixed(1)}" y2="${cy}" class="eb"/>`;
      }
      if (pu > 0) {
        g += `<line x1="${cx}" y1="${Y(o.pressure_gigapascal - pu).toFixed(1)}" x2="${cx}" y2="${Y(o.pressure_gigapascal + pu).toFixed(1)}" class="eb"/>`;
      }
      g += `<circle cx="${cx}" cy="${cy}" r="4" class="pt" data-tip="${id} · T ${o.temperature_celsius} °C · P ${o.pressure_gigapascal.toFixed(2)} GPa"/>`;
    });
    r.interpreted_boundaries.forEach(b => {
      let segment = [];
      const flush = () => {
        if (segment.length > 1) {
          g += `<polyline points="${segment.map(p => X(p.t).toFixed(1) + "," + Y(p.p).toFixed(1)).join(" ")}" class="pub"/>`;
        }
        segment = [];
      };
      sample_curve(b).forEach(s => { if (s.p === null) flush(); else segment.push(s); });
      flush();
    });
    g += `</g>`;
    svg += g;
  });

  const target = records.find(r => r.reaction_identifier === selected);
  if (target && target.observations.length >= 2) {
    const { fit, design } = await analysis_for(selected);
    if (seq !== plot_seq) return;
    const sid = escape_html(selected);
    plot_owners.push(selected, selected, selected);
    let g = `<g class="series" data-owner="${sid}">`;
    const upper = fit.line.map(p => `${X(p.temperature_celsius).toFixed(1)},${Y(p.pressure_gigapascal + p.band_gigapascal).toFixed(1)}`).join(" ");
    const lower = [...fit.line].reverse().map(p => `${X(p.temperature_celsius).toFixed(1)},${Y(p.pressure_gigapascal - p.band_gigapascal).toFixed(1)}`).join(" ");
    g += `<polygon points="${upper} ${lower}" class="fit-band"/>`;
    g += `<polyline points="${fit.line.map(p => X(p.temperature_celsius).toFixed(1) + "," + Y(p.pressure_gigapascal).toFixed(1)).join(" ")}" class="fit-line"/>`;
    g += `</g><g class="series" data-owner="${sid}">`;
    const top = design.candidates.slice(0, 5);
    const largest = Math.max(...top.map(c => c.expected_variance_drop), 1e-12);
    top.forEach(c => {
      const r = 5 + 7 * c.expected_variance_drop / largest;
      g += `<polygon points="${star_points(X(c.temperature_celsius), Y(c.pressure_gigapascal), r)}" class="star" data-tip="candidate · T ${c.temperature_celsius.toFixed(0)} °C · P ${c.pressure_gigapascal.toFixed(2)} GPa"/>`;
    });
    g += `</g><g class="series" data-owner="${sid}"></g>`;
    svg += g;
  }
  svg += `</g>`;

  plot_svg.innerHTML = svg;
  apply_spotlight();
}

function schedule_refresh(immediate = false) {
  if (immediate) { refresh(); return; }
  clearTimeout(debounce_timer);
  debounce_timer = setTimeout(refresh, 120);
}

document.addEventListener("keydown", event => {
  if (event.key === "/" && document.activeElement !== query_input) { event.preventDefault(); query_input.focus(); }
});
query_input.addEventListener("input", () => schedule_refresh(false));
type_select.addEventListener("change", () => schedule_refresh(true));
document.getElementById("export").addEventListener("click", () => {
  window.location = "/export?" + new URLSearchParams({ query: query_input.value, reaction_type: type_select.value }).toString();
});

// Hover is delegated to the list itself: gaps between rows and moves from
// one row to the next switch emphasis directly, so the plot never flashes
// back to full brightness mid-scroll.
const list_el = document.getElementById("reaction_list");
list_el.addEventListener("mouseover", event => {
  const link = event.target.closest("a");
  if (link) emphasize(link.dataset.id);
});
list_el.addEventListener("mouseleave", clear_emphasis);

// Console-style tooltip: point markers carry their own readout.
plot_svg.addEventListener("mousemove", event => {
  const mark = event.target.closest("[data-tip]");
  const body = plot_svg.parentElement.getBoundingClientRect();
  if (!mark) { plot_tip.hidden = true; return; }
  const [tip, detail] = mark.getAttribute("data-tip").split(" · ");
  plot_tip.innerHTML = `<strong>${escape_html(tip)}</strong><br><span>${escape_html(detail || "")}</span>`;
  plot_tip.hidden = false;
  let x = event.clientX - body.left + 14, y = event.clientY - body.top + 14;
  if (x + 200 > body.width) x -= 214;
  if (y + 60 > body.height) y -= 74;
  plot_tip.style.left = x + "px";
  plot_tip.style.top = y + "px";
});
plot_svg.addEventListener("mouseleave", () => { plot_tip.hidden = true; });

const initial = read_state();
query_input.value = initial.query;
type_select.value = initial.reaction_type;
selected = initial.selected;
refresh();
