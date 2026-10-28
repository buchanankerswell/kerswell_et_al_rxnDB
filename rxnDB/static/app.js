/* rxnDB search page logic. Same endpoints serve browsers and agents. */

const query_input = document.getElementById("query");
const type_select = document.getElementById("reaction_type");
const count_el = document.getElementById("count");
const obs_count_el = document.getElementById("obs_count");
const plot_svg = document.getElementById("plot");
const plot_tip = document.getElementById("plot_tip");
const plot_reset = document.getElementById("plot_reset");
const tab_links = Array.from(document.querySelectorAll(".tabs-inner a[data-tab]"));
const tab_indicator = document.getElementById("tab_indicator");
const view_reactions = document.getElementById("view-reactions");
const view_observations = document.getElementById("view-observations");

function tab_from_path(pathname) {
  return pathname.replace(/\/+$/, "").endsWith("/observations") ? "observations" : "reactions";
}

function path_for_tab(tab) {
  return tab === "observations" ? "/observations" : "/";
}

function read_state() {
  const params = new URLSearchParams(location.search);
  return {
    query: params.get("query") || "",
    reaction_type: params.get("reaction_type") || "",
    selected: params.get("selected") || "",
    tab: tab_from_path(location.pathname),
  };
}

function write_state(state, options) {
  const params = new URLSearchParams();
  if (state.query) params.set("query", state.query);
  if (state.reaction_type) params.set("reaction_type", state.reaction_type);
  if (state.selected) params.set("selected", state.selected);
  const query = params.toString();
  const url = path_for_tab(state.tab) + (query ? "?" + query : "");
  if (options && options.push) history.pushState(null, "", url);
  else history.replaceState(null, "", url);
}

function escape_html(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function symbols(reaction) {
  return [...reaction.reactants, ...reaction.products].map((p) => p.mineral_symbol).join(" + ");
}

function phase_names(reaction) {
  return [...reaction.reactants, ...reaction.products].map((p) => p.mineral_name).join(" + ");
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
    const t = low + ((high - low) * i) / 39;
    const p =
      boundary.pressure_intercept_gigapascal +
      boundary.pressure_slope_gigapascal_per_celsius * t +
      boundary.pressure_curvature_gigapascal_per_celsius_squared * t * t +
      boundary.pressure_cubic_gigapascal_per_celsius_cubed * t * t * t;
    return { t, p: p < floor || (ceiling !== null && ceiling !== undefined && p > ceiling) ? null : p };
  });
}

let selected = "";
let active_tab = "reactions";
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

// Pan/zoom view state. full_view fits every point of the current filter set;
// view is the visible window. draw_cache holds the last computed series so
// pans and zooms redraw without refetching or refitting.
let view = null;
let full_view = null;
let draw_cache = null;
let draw_queued = false;

const SVG_W = 720,
  SVG_H = 560;
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
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
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
  groups.forEach((g) => {
    g.setAttribute("opacity", focus !== null && g.dataset.owner === focus ? "1" : String(DIM_OPACITY));
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

function move_tab_indicator() {
  if (!tab_indicator || tab_links.length === 0) return;
  const active = tab_links.find((a) => a.dataset.tab === active_tab) || tab_links[0];
  const parent_rect = active.parentElement.getBoundingClientRect();
  const rect = active.getBoundingClientRect();
  tab_indicator.style.width = rect.width + "px";
  tab_indicator.style.transform = `translateX(${rect.left - parent_rect.left}px)`;
}

// Console-style page switch: slide the underline, crossfade the panels, and
// push a history entry so back/forward moves between / and /observations.
function set_tab(tab, options) {
  if (tab !== "observations") tab = "reactions";
  const changed = tab !== active_tab;
  active_tab = tab;
  tab_links.forEach((a) => {
    a.setAttribute("aria-current", String(a.dataset.tab === active_tab));
  });
  const show_reactions = active_tab === "reactions";
  view_reactions.hidden = !show_reactions;
  view_observations.hidden = show_reactions;
  for (const panel of [view_reactions, view_observations]) {
    if (!panel.hidden) {
      panel.classList.remove("switch-in");
      void panel.offsetWidth;
      panel.classList.add("switch-in");
    }
  }
  move_tab_indicator();
  write_state(
    { query: query_input.value, reaction_type: type_select.value, selected, tab: active_tab },
    { push: changed && !(options && options.replace) },
  );
  if (changed && show_reactions && last_records.length > 0) {
    clearTimeout(plot_timer);
    plot_pending = null;
    render_plot(last_records);
  }
}

async function analysis_for(identifier) {
  if (analysis_cache.has(identifier)) return analysis_cache.get(identifier);
  const [fit, design] = await Promise.all([
    (
      await fetch("/fit/boundary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reaction_identifier: identifier }),
      })
    ).json(),
    (
      await fetch("/design/next-point", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reaction_identifier: identifier, candidate_count: 20 }),
      })
    ).json(),
  ]);
  const result = { fit, design };
  analysis_cache.set(identifier, result);
  return result;
}

async function refresh() {
  const seq = ++refresh_seq;
  const state = { query: query_input.value, reaction_type: type_select.value, selected, tab: active_tab };
  write_state(state);
  if (list_controller) list_controller.abort();
  list_controller = new AbortController();
  count_el.textContent = "Searching…";
  if (obs_count_el) obs_count_el.textContent = "Searching…";
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
  count_el.textContent = total === 0 ? "No reactions match." : `${total} reaction${total === 1 ? "" : "s"}`;

  document.getElementById("reaction_list").innerHTML = records
    .map(
      (r) =>
        `<li><a href="#" data-id="${escape_html(r.reaction_identifier)}" aria-current="${r.reaction_identifier === selected}">` +
        `<span class="row-main"><span class="id">${escape_html(r.reaction_identifier)}</span>` +
        `${suspect(r) ? `<span class="pill">review</span>` : ""}</span>` +
        `<span class="sym">${escape_html(symbols(r))}</span><span class="name-cell">${escape_html(phase_names(r))}</span></a></li>`,
    )
    .join("");
  document.querySelectorAll("#reaction_list a").forEach((link) =>
    link.addEventListener("click", (event) => {
      event.preventDefault();
      select(link.dataset.id);
    }),
  );

  schedule_plot(records);

  let observation_total = 0;
  const rows = records.flatMap((r) => {
    observation_total += r.observations.length;
    const phases = symbols(r);
    const names = phase_names(r);
    return r.observations.map((o) => {
      const id = escape_html(r.reaction_identifier);
      const type = escape_html(r.reaction_type);
      const source = escape_html(r.source.short_citation);
      const phase_cell = `<div class="sym-cell">${escape_html(phases)}</div><div class="name-cell">${escape_html(names)}</div>`;
      const t = `<td class="num">${o.temperature_celsius}</td><td class="num">${o.pressure_gigapascal.toFixed(2)}</td>`;
      return `<tr><td>${id}</td><td>${phase_cell}</td>${t}<td>${type}</td><td>${source}</td></tr>`;
    });
  });
  document.querySelector("#table tbody").innerHTML = rows.join("");
  if (obs_count_el) {
    obs_count_el.textContent =
      observation_total === 0 && records.length === 0
        ? "No observations match."
        : `${observation_total} observation${observation_total === 1 ? "" : "s"} · ${total} reaction${total === 1 ? "" : "s"}`;
  }
}

// The list and table redraw cheaply on every keystroke, but a full plot
// redraw is slow with hundreds of series, so filter changes only schedule
// the plot trailing-edge: typing stays instant and the plot catches up.
// While the observations tab is showing the plot stays deferred and renders
// on the way back to the reactions tab.
function schedule_plot(records) {
  if (active_tab !== "reactions") {
    plot_pending = records;
    return;
  }
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
  selected = selected === identifier ? "" : identifier;
  write_state({ query: query_input.value, reaction_type: type_select.value, selected, tab: active_tab });
  document.querySelectorAll("#reaction_list a").forEach((other) => {
    other.setAttribute("aria-current", String(other.dataset.id === selected));
  });
  clearTimeout(plot_timer);
  plot_pending = null;
  if (active_tab === "reactions") await render_plot(last_records);
}

async function render_plot(records) {
  const seq = ++plot_seq;

  const points = [];
  records.forEach((r) => {
    r.observations.forEach((o) => points.push({ t: o.temperature_celsius, p: o.pressure_gigapascal }));
    r.interpreted_boundaries.forEach((b) =>
      sample_curve(b).forEach((s) => {
        if (s.p !== null) points.push({ t: s.t, p: s.p });
      }),
    );
  });

  if (points.length === 0) {
    plot_owners = [];
    draw_cache = null;
    view = null;
    full_view = null;
    plot_svg.innerHTML = `<text x="${SVG_W / 2}" y="${SVG_H / 2}" text-anchor="middle" class="plot-empty">No points in this filter set.</text>`;
    plot_tip.hidden = true;
    plot_reset.hidden = true;
    return;
  }

  let tmin = Math.min(...points.map((d) => d.t));
  let tmax = Math.max(...points.map((d) => d.t));
  let pmin = Math.min(...points.map((d) => d.p));
  let pmax = Math.max(...points.map((d) => d.p));
  if (tmax - tmin < 1e-9) {
    tmin -= 1;
    tmax += 1;
  }
  if (pmax - pmin < 1e-9) {
    pmin -= 0.1;
    pmax += 0.1;
  }
  const tpad = (tmax - tmin) * 0.04,
    ppad = (pmax - pmin) * 0.06;
  tmin -= tpad;
  tmax += tpad;
  pmin -= ppad;
  pmax += ppad;
  full_view = { tmin, tmax, pmin, pmax };
  // The zoom/pan window persists across searches and selections; it only
  // (re)fits when empty or on explicit reset.
  if (view === null) view = { ...full_view };

  let fit = null,
    design = null;
  const target = records.find((r) => r.reaction_identifier === selected);
  if (target && target.observations.length >= 2) {
    const result = await analysis_for(selected);
    if (seq !== plot_seq) return;
    fit = result.fit;
    design = result.design;
  }
  draw_cache = { records, fit, design };
  draw_plot();
}

function views_equal(a, b) {
  if (!a || !b) return true;
  const keys = ["tmin", "tmax", "pmin", "pmax"];
  return keys.every((k) => Math.abs(a[k] - b[k]) <= 1e-9 * Math.max(1, Math.abs(a[k]), Math.abs(b[k])));
}

function request_draw() {
  if (draw_queued || !draw_cache) return;
  draw_queued = true;
  requestAnimationFrame(() => {
    draw_queued = false;
    draw_plot();
  });
}

function draw_plot() {
  if (!draw_cache || !view) return;
  const { records, fit, design } = draw_cache;
  const { tmin, tmax, pmin, pmax } = view;

  const PW = SVG_W - PAD.left - PAD.right;
  const PH = SVG_H - PAD.top - PAD.bottom;
  const X = (t) => PAD.left + ((t - tmin) / (tmax - tmin)) * PW;
  const Y = (p) => PAD.top + (1 - (p - pmin) / (pmax - pmin)) * PH;

  const yticks = ticks(pmin, pmax);
  const xticks = ticks(tmin, tmax);
  const ystep = yticks.length > 1 ? yticks[1] - yticks[0] : 1;
  const xstep = xticks.length > 1 ? xticks[1] - xticks[0] : 1;

  let svg = `<defs><clipPath id="plot_clip"><rect x="${PAD.left}" y="${PAD.top}" width="${PW}" height="${PH}"/></clipPath></defs>`;

  yticks.forEach((v, i) => {
    const yy = Y(v).toFixed(1);
    const solid = i === 0;
    svg += `<line x1="${PAD.left}" y1="${yy}" x2="${SVG_W - PAD.right}" y2="${yy}" class="${solid ? "grid-solid" : "grid-line"}"/>`;
    const tick_label = escape_html(format_tick(v, ystep));
    svg += `<text x="${PAD.left - 8}" y="${yy}" text-anchor="end" dominant-baseline="central" class="tick">${tick_label}</text>`;
  });
  xticks.forEach((v) => {
    svg += `<text x="${X(v).toFixed(1)}" y="${PAD.top + PH + 18}" text-anchor="middle" class="tick">${escape_html(format_tick(v, xstep))}</text>`;
  });
  svg += `<text x="${PAD.left + PW / 2}" y="${SVG_H - 4}" text-anchor="middle" class="axis-title">Temperature (°C)</text>`;
  const mid_y = PAD.top + PH / 2;
  svg += `<text x="12" y="${mid_y}" text-anchor="middle" transform="rotate(-90 12 ${mid_y})" class="axis-title">Pressure (GPa)</text>`;

  svg += `<g clip-path="url(#plot_clip)">`;
  plot_owners = [];
  records.forEach((r) => {
    const id = escape_html(r.reaction_identifier);
    plot_owners.push(r.reaction_identifier);
    let g = `<g class="series" data-owner="${id}">`;
    const phases = symbols(r);
    const names = phase_names(r);
    r.observations.forEach((o) => {
      const cx = X(o.temperature_celsius).toFixed(1),
        cy = Y(o.pressure_gigapascal).toFixed(1);
      const tu = o.temperature_uncertainty_celsius || 0;
      const pu = o.pressure_uncertainty_gigapascal || 0;
      if (tu > 0) {
        const x1 = X(o.temperature_celsius - tu).toFixed(1);
        const x2 = X(o.temperature_celsius + tu).toFixed(1);
        g += `<line x1="${x1}" y1="${cy}" x2="${x2}" y2="${cy}" class="eb"/>`;
      }
      if (pu > 0) {
        const y1 = Y(o.pressure_gigapascal - pu).toFixed(1);
        const y2 = Y(o.pressure_gigapascal + pu).toFixed(1);
        g += `<line x1="${cx}" y1="${y1}" x2="${cx}" y2="${y2}" class="eb"/>`;
      }
      const tip = `${id} · ${escape_html(phases)} · ${escape_html(names)}`;
      const where = `${o.temperature_celsius} °C · ${o.pressure_gigapascal.toFixed(2)} GPa`;
      g += `<circle cx="${cx}" cy="${cy}" r="4" class="pt" data-tip="${tip} · ${where}"/>`;
    });
    r.interpreted_boundaries.forEach((b) => {
      let segment = [];
      const flush = () => {
        if (segment.length > 1) {
          g += `<polyline points="${segment.map((p) => X(p.t).toFixed(1) + "," + Y(p.p).toFixed(1)).join(" ")}" class="pub"/>`;
        }
        segment = [];
      };
      sample_curve(b).forEach((s) => {
        if (s.p === null) flush();
        else segment.push(s);
      });
      flush();
    });
    g += `</g>`;
    svg += g;
  });

  const sid = escape_html(selected);
  if (fit && design) {
    const sel_rec = records.find((r) => r.reaction_identifier === selected);
    const sel_phases = sel_rec ? symbols(sel_rec) : "";
    const sel_names = sel_rec ? phase_names(sel_rec) : "";
    plot_owners.push(selected, selected, selected);
    let g = `<g class="series" data-owner="${sid}">`;
    const upper = fit.line.map((p) => `${X(p.temperature_celsius).toFixed(1)},${Y(p.pressure_gigapascal + p.band_gigapascal).toFixed(1)}`).join(" ");
    const lower = [...fit.line]
      .reverse()
      .map((p) => `${X(p.temperature_celsius).toFixed(1)},${Y(p.pressure_gigapascal - p.band_gigapascal).toFixed(1)}`)
      .join(" ");
    g += `<polygon points="${upper} ${lower}" class="fit-band"/>`;
    const line_points = fit.line.map((p) => `${X(p.temperature_celsius).toFixed(1)},${Y(p.pressure_gigapascal).toFixed(1)}`);
    g += `<polyline points="${line_points.join(" ")}" class="fit-line"/>`;
    g += `</g><g class="series" data-owner="${sid}">`;
    const top = design.candidates.slice(0, 5);
    const largest = Math.max(...top.map((c) => c.expected_variance_drop), 1e-12);
    top.forEach((c) => {
      const r = 5 + (7 * c.expected_variance_drop) / largest;
      const tip = `candidate (${sid}) · ${escape_html(sel_phases)} · ${escape_html(sel_names)}`;
      const where = `${c.temperature_celsius.toFixed(0)} °C · ${c.pressure_gigapascal.toFixed(2)} GPa`;
      g += `<polygon points="${star_points(X(c.temperature_celsius), Y(c.pressure_gigapascal), r)}" class="star" data-tip="${tip} · ${where}"/>`;
    });
    g += `</g><g class="series" data-owner="${sid}"></g>`;
    svg += g;
  }
  svg += `</g>`;

  plot_svg.innerHTML = svg;
  apply_spotlight();
  plot_reset.hidden = views_equal(view, full_view);
}

// Pan and zoom. The wheel zooms around the cursor, drag pans, and a
// double-click (or the Reset view button) returns to the full filter set.
// Redraws reuse the cached series and are throttled to one per frame.
function svg_point(event) {
  const rect = plot_svg.getBoundingClientRect();
  return {
    x: ((event.clientX - rect.left) / rect.width) * SVG_W,
    y: ((event.clientY - rect.top) / rect.height) * SVG_H,
  };
}

function plot_area() {
  return { PW: SVG_W - PAD.left - PAD.right, PH: SVG_H - PAD.top - PAD.bottom };
}

function clamp_view() {
  if (!full_view) return;
  const ft = full_view.tmax - full_view.tmin;
  const fp = full_view.pmax - full_view.pmin;
  const tspan = Math.min(Math.max(view.tmax - view.tmin, ft * 1e-4), ft * 1e3);
  const pspan = Math.min(Math.max(view.pmax - view.pmin, fp * 1e-4), fp * 1e3);
  const tc = (view.tmin + view.tmax) / 2,
    pc = (view.pmin + view.pmax) / 2;
  view.tmin = tc - tspan / 2;
  view.tmax = tc + tspan / 2;
  view.pmin = pc - pspan / 2;
  view.pmax = pc + pspan / 2;
}

function reset_view() {
  if (!full_view) return;
  view = { ...full_view };
  request_draw();
}

plot_svg.addEventListener(
  "wheel",
  (event) => {
    if (!draw_cache || !view) return;
    event.preventDefault();
    const { PW, PH } = plot_area();
    const pt = svg_point(event);
    const anchor_t = view.tmin + ((pt.x - PAD.left) / PW) * (view.tmax - view.tmin);
    const anchor_p = view.pmax - ((pt.y - PAD.top) / PH) * (view.pmax - view.pmin);
    const factor = Math.exp(event.deltaY * 0.0015);
    view.tmin = anchor_t - (anchor_t - view.tmin) * factor;
    view.tmax = anchor_t + (view.tmax - anchor_t) * factor;
    view.pmin = anchor_p - (anchor_p - view.pmin) * factor;
    view.pmax = anchor_p + (view.pmax - anchor_p) * factor;
    clamp_view();
    request_draw();
  },
  { passive: false },
);

let pan_start = null;
let suppress_click = false;
// Pointer capture retargets later events at the svg root, so the pressed
// series is recorded here for the pointerup select below.
let down_owner = null;
plot_svg.addEventListener("pointerdown", (event) => {
  if (!draw_cache || !view) return;
  const down_series = event.target.closest("g.series");
  down_owner = (down_series && down_series.dataset.owner) || null;
  if (event.pointerType === "mouse" && event.button !== 0) return;
  const pt = svg_point(event);
  pan_start = { x: pt.x, y: pt.y, view: { ...view } };
  suppress_click = false;
  plot_svg.setPointerCapture(event.pointerId);
  plot_svg.classList.add("panning");
  plot_tip.hidden = true;
});
plot_svg.addEventListener("pointermove", (event) => {
  if (!pan_start) return;
  const pt = svg_point(event);
  const { PW, PH } = plot_area();
  const tspan = pan_start.view.tmax - pan_start.view.tmin;
  const pspan = pan_start.view.pmax - pan_start.view.pmin;
  const dt = ((pt.x - pan_start.x) / PW) * tspan;
  const dp = ((pt.y - pan_start.y) / PH) * pspan;
  view.tmin = pan_start.view.tmin - dt;
  view.tmax = pan_start.view.tmax - dt;
  view.pmin = pan_start.view.pmin + dp;
  view.pmax = pan_start.view.pmax + dp;
  if (Math.hypot(pt.x - pan_start.x, pt.y - pan_start.y) > 4) suppress_click = true;
  request_draw();
});
function end_pan() {
  if (!pan_start) return;
  pan_start = null;
  plot_svg.classList.remove("panning");
}
plot_svg.addEventListener("pointercancel", () => {
  down_owner = null;
});
plot_svg.addEventListener("pointerup", end_pan);
plot_svg.addEventListener("pointercancel", end_pan);
// A drag across the svg must never become a text selection wash.
plot_svg.addEventListener("selectstart", (event) => event.preventDefault());
plot_svg.addEventListener("dblclick", reset_view);
plot_reset.addEventListener("click", reset_view);

// Ctrl-click (or Cmd-click) a series to select that reaction, then centre it
// in the side card. A drag ending in a click never selects; on macOS the
// Ctrl-triggered context menu is suppressed so Ctrl-click just selects.
// Ctrl-click (or Cmd-click) a series to select that reaction, then centre it
// in the side card. Handled on pointerup rather than click so the gesture
// works uniformly: macOS Ctrl-click arrives as a right-click and never
// produces a click event. A drag ending in a pointerup never selects.
plot_svg.addEventListener("pointerup", async (event) => {
  const owner = down_owner;
  down_owner = null;
  if (suppress_click) {
    suppress_click = false;
    return;
  }
  if (!(event.ctrlKey || event.metaKey)) return;
  if (!owner) return;
  event.preventDefault();
  await select(owner);
  const link = document.querySelector(`#reaction_list a[data-id="${owner}"]`);
  if (link) link.scrollIntoView({ block: "center", behavior: "smooth" });
});
plot_svg.addEventListener("contextmenu", (event) => {
  if (event.ctrlKey) event.preventDefault();
});

function schedule_refresh(immediate = false) {
  if (immediate) {
    refresh();
    return;
  }
  clearTimeout(debounce_timer);
  debounce_timer = setTimeout(refresh, 120);
}

document.addEventListener("keydown", (event) => {
  if (event.key === "/" && document.activeElement !== query_input) {
    event.preventDefault();
    query_input.focus();
  }
  if (event.metaKey || event.ctrlKey) plot_svg.classList.add("select-mod");
});
document.addEventListener("keyup", (event) => {
  if (!event.metaKey && !event.ctrlKey) plot_svg.classList.remove("select-mod");
});
window.addEventListener("blur", () => plot_svg.classList.remove("select-mod"));
query_input.addEventListener("input", () => schedule_refresh(false));
type_select.addEventListener("change", () => schedule_refresh(true));
document.getElementById("export").addEventListener("click", () => {
  window.location = "/export?" + new URLSearchParams({ query: query_input.value, reaction_type: type_select.value }).toString();
});

// Hover is delegated to the list itself: gaps between rows and moves from
// one row to the next switch emphasis directly, so the plot never flashes
// back to full brightness mid-scroll.
const list_el = document.getElementById("reaction_list");
list_el.addEventListener("mouseover", (event) => {
  const link = event.target.closest("a");
  if (link) emphasize(link.dataset.id);
});
list_el.addEventListener("mouseleave", clear_emphasis);

// Console-style tooltip: point markers carry their own readout. Hovering any
// part of a series also emphasizes that whole reaction, matching list hover.
plot_svg.addEventListener("mousemove", (event) => {
  if (pan_start) {
    plot_tip.hidden = true;
    return;
  }
  const series = event.target.closest("g.series");
  if (series && series.dataset.owner) emphasize(series.dataset.owner);
  else clear_emphasis();
  const mark = event.target.closest("[data-tip]");
  const body = plot_svg.parentElement.getBoundingClientRect();
  if (!mark) {
    plot_tip.hidden = true;
    return;
  }
  const [title, phases, names, temp, pressure] = mark.getAttribute("data-tip").split(" · ");
  plot_tip.innerHTML =
    `<strong>${escape_html(title)}</strong>` +
    (phases ? `<br><span>${escape_html(phases)}</span>` : "") +
    (names ? `<br><span>${escape_html(names)}</span>` : "") +
    (temp ? `<br><span>Temperature: ${escape_html(temp)}</span>` : "") +
    (pressure ? `<br><span>Pressure: ${escape_html(pressure)}</span>` : "");
  plot_tip.hidden = false;
  let x = event.clientX - body.left + 14,
    y = event.clientY - body.top + 14;
  if (x + 200 > body.width) x -= 214;
  if (y + 60 > body.height) y -= 74;
  plot_tip.style.left = x + "px";
  plot_tip.style.top = y + "px";
});
plot_svg.addEventListener("mouseleave", () => {
  plot_tip.hidden = true;
  clear_emphasis();
});

const initial = read_state();
query_input.value = initial.query;
type_select.value = initial.reaction_type;
selected = initial.selected;
active_tab = initial.tab;
tab_links.forEach((a) => {
  a.setAttribute("aria-current", String(a.dataset.tab === active_tab));
});
view_reactions.hidden = active_tab !== "reactions";
view_observations.hidden = active_tab !== "observations";
tab_links.forEach((a) => {
  a.addEventListener("click", (event) => {
    event.preventDefault();
    if (a.dataset.tab === active_tab) return;
    query_input.focus({ preventScroll: true });
    set_tab(a.dataset.tab, { push: true });
  });
});
window.addEventListener("popstate", () => {
  const state = read_state();
  query_input.value = state.query;
  type_select.value = state.reaction_type;
  selected = state.selected;
  document.querySelectorAll("#reaction_list a").forEach((other) => {
    other.setAttribute("aria-current", String(other.dataset.id === selected));
  });
  if (state.tab !== active_tab) set_tab(state.tab, { replace: true });
  refresh();
});
window.addEventListener("resize", move_tab_indicator);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(move_tab_indicator);
requestAnimationFrame(move_tab_indicator);
setTimeout(move_tab_indicator, 100);
refresh();
