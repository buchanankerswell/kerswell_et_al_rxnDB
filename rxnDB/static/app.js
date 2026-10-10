/* rxnDB search page logic. Same endpoints serve browsers and agents. */

const query_input = document.getElementById("query");
const type_select = document.getElementById("reaction_type");
const count_el = document.getElementById("count");

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

function boundary_trace(reaction, boundary) {
  const low = boundary.valid_temperature_min_celsius ?? 400;
  const high = boundary.valid_temperature_max_celsius ?? 1800;
  const floor = Math.max(boundary.valid_pressure_min_gigapascal ?? 0, 0);
  const ceiling = boundary.valid_pressure_max_gigapascal ?? null;
  const grid = Array.from({ length: 40 }, (_, i) => low + (high - low) * i / 39);
  return {
    x: grid,
    y: grid.map(t => {
      const p = boundary.pressure_intercept_gigapascal
        + boundary.pressure_slope_gigapascal_per_celsius * t
        + boundary.pressure_curvature_gigapascal_per_celsius_squared * t * t
        + boundary.pressure_cubic_gigapascal_per_celsius_cubed * t * t * t;
      return (p < floor || (ceiling !== null && p > ceiling)) ? null : p;
    }),
    mode: "lines", type: "scatter", line: { dash: "dash" },
    name: reaction.reaction_identifier + " (published)",
  };
}

function suspect(reaction) {
  return reaction.extensions && reaction.extensions.verification_status === "suspect";
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
let trace_owners = [];
let trace_opacity = [];

function plot_layout() {
  const ink = getComputedStyle(document.body).color;
  const styles = getComputedStyle(document.documentElement);
  const line = styles.getPropertyValue("--line").trim() || "#e1e3e5";
  const grid = styles.getPropertyValue("--grid").trim() || "#eef0f2";
  const axis = {
    showline: true,
    linewidth: 1,
    linecolor: line,
    mirror: true,
    showgrid: true,
    gridcolor: grid,
    gridwidth: 1,
    zeroline: false,
    ticks: "outside",
    tickfont: { size: 14 },
  };
  return {
    margin: { l: 62, r: 16, t: 24, b: 82 },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif", size: 14, color: ink },
    xaxis: { ...axis, title: { text: "Temperature (°C)", font: { size: 18 } } },
    yaxis: { ...axis, title: { text: "Pressure (GPa)", font: { size: 18 } } },
    showlegend: false,
    hovermode: "closest",
  };
}

const DIM_OPACITY = 0.5;
let hovered = null;
const PLOT_LIMIT = 200;

function apply_spotlight() {
  const panel = document.getElementById("plot");
  if (!panel.data || panel.data.length !== trace_owners.length) return;
  const focus = hovered || selected || null;
  if (focus !== null && !trace_owners.includes(focus)) return;
  Plotly.restyle(panel, { opacity: trace_owners.map((owner, i) =>
    (focus !== null && owner === focus ? trace_opacity[i] : DIM_OPACITY)) });
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
    `<span class="id">${escape_html(r.reaction_identifier)}</span>` +
    `<span class="sym">${escape_html(symbols(r))}</span>` +
    `${suspect(r) ? `<span class="pill">review</span>` : ""}</a></li>`).join("");
  document.querySelectorAll("#reaction_list a").forEach(link =>
    link.addEventListener("click", event => { event.preventDefault(); select(link.dataset.id); }));

  schedule_plot(records);

  const rows = records.flatMap(r =>
    r.observations.map(o => `<tr><td>${escape_html(r.reaction_identifier)}</td><td>${o.temperature_celsius}</td><td>${o.pressure_gigapascal.toFixed(2)}</td><td>${escape_html(o.experimental_outcome)}</td><td>${escape_html(r.source.short_citation)}</td></tr>`)
  );
  document.querySelector("#table tbody").innerHTML = rows.join("");
}

// The list and table redraw cheaply on every keystroke, but a full plot
// redraw is slow with hundreds of traces, so filter changes only schedule
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
  const traces = plotted.flatMap(r => [
    {
      x: r.observations.map(o => o.temperature_celsius),
      y: r.observations.map(o => o.pressure_gigapascal),
      error_x: { array: r.observations.map(o => o.temperature_uncertainty_celsius) },
      error_y: { array: r.observations.map(o => o.pressure_uncertainty_gigapascal) },
      mode: "markers", type: "scatter", name: r.reaction_identifier,
    },
    ...r.interpreted_boundaries.map(b => boundary_trace(r, b)),
  ]);
  trace_owners = plotted.flatMap(r => [
    r.reaction_identifier,
    ...r.interpreted_boundaries.map(() => r.reaction_identifier),
  ]);

  const target = records.find(r => r.reaction_identifier === selected);
  if (target && target.observations.length >= 2) {
    const { fit, design } = await analysis_for(selected);
    if (seq !== plot_seq) return;
    traces.push({
      x: fit.line.map(p => p.temperature_celsius), y: fit.line.map(p => p.pressure_gigapascal),
      mode: "lines", type: "scatter", name: selected + " (fit)",
    });
    traces.push({
      x: [...fit.line.map(p => p.temperature_celsius), ...fit.line.map(p => p.temperature_celsius).reverse()],
      y: [...fit.line.map(p => p.pressure_gigapascal + p.band_gigapascal), ...fit.line.map(p => p.pressure_gigapascal - p.band_gigapascal).reverse()],
      fill: "toself", type: "scatter", mode: "none", name: selected + " (95% band)", opacity: 0.2,
    });
    const top = design.candidates.slice(0, 5);
    const drops = top.map(c => c.expected_variance_drop);
    const largest = Math.max(...drops, 1e-12);
    traces.push({
      x: top.map(c => c.temperature_celsius), y: top.map(c => c.pressure_gigapascal),
      mode: "markers", type: "scatter", name: "next-point candidates",
      marker: { size: drops.map(d => 8 + 20 * d / largest), symbol: "star" },
    });
    trace_owners.push(selected, selected, selected);
  }

  trace_opacity = traces.map(t => t.opacity ?? 1);
  const layout = plot_layout();
  if (records.length > plotted.length) {
    layout.margin.t = 48;
    layout.title = { text: `Plot shows first ${plotted.length} of ${records.length} reactions`, font: { size: 13 } };
  }
  await Plotly.react("plot", traces, layout);
  if (seq !== plot_seq) return;
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

const initial = read_state();
query_input.value = initial.query;
type_select.value = initial.reaction_type;
selected = initial.selected;
refresh();
