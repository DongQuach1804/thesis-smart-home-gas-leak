/* Gas Leak Intelligence — frontend dashboard logic
 * Single bundle, no build step. Talks to the backend via fetch + SSE.
 */
(() => {
  "use strict";

  const API = (window.__APP_CONFIG__ && window.__APP_CONFIG__.api) || "/api";

  const POLL_LATEST_MS   = 3000;
  const POLL_OVERVIEW_MS = 15000;
  const POLL_DEVICES_MS  = 20000;
  const POLL_ALERTS_MS   = 20000;
  const MAX_CHART_PTS    = 120;

  const RISK_META = {
    NORMAL:  { cls: "badge--normal",  hex: "#22c55e" },
    WARNING: { cls: "badge--warning", hex: "#f59e0b" },
    ALERT:   { cls: "badge--alert",   hex: "#ef4444" },
  };

  const state = {
    deviceId:  "",
    rangeMins: 30,
    history:   [],
    alerts:    [],
  };

  // ─── Utilities ────────────────────────────────────────────────────────────
  const $  = (id) => document.getElementById(id);
  const fmtTime = (d) => new Date(d).toLocaleTimeString("vi-VN", { hour12: false });
  const fmt = (n, digits = 1) => (Number.isFinite(n) ? n.toFixed(digits) : "—");
  const safe = (fn) => (...a) => { try { return fn(...a); } catch (e) { console.error(e); } };
  const ESC_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ESC_MAP[c]);

  let thresholds = { gasPpmWarning: 400, gasPpmAlert: 700 };

  function toast(msg, kind = "info") {
    const el = document.createElement("div");
    el.className = "toast toast--" + kind;
    el.textContent = msg;
    $("toasts").appendChild(el);
    setTimeout(() => { el.classList.add("toast--out"); setTimeout(() => el.remove(), 400); }, 4000);
  }

  // ─── Clock ────────────────────────────────────────────────────────────────
  setInterval(() => { $("clock").textContent = fmtTime(new Date()); }, 1000);
  $("clock").textContent = fmtTime(new Date());

  // ─── Navigation ───────────────────────────────────────────────────────────
  document.querySelectorAll(".navlink").forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const view = a.dataset.view;
      document.querySelectorAll(".navlink").forEach(n => n.classList.toggle("is-active", n === a));
      document.querySelectorAll(".view").forEach(v => v.classList.toggle("is-active", v.dataset.view === view));
      $("view-title").textContent = a.textContent.trim();
      if (view === "devices")   refreshDevices();
      if (view === "alerts")    refreshAlertsTable();
      if (view === "analytics") renderAnalytics();
    });
  });

  // ─── Range control ────────────────────────────────────────────────────────
  document.querySelectorAll("#range-control button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#range-control button").forEach(b => b.classList.toggle("is-active", b === btn));
      state.rangeMins = Number(btn.dataset.range);
      bootHistory();
      refreshStats();
    });
  });

  // ─── Device select ────────────────────────────────────────────────────────
  $("device-select").addEventListener("change", (e) => {
    state.deviceId = e.target.value;
    bootHistory();
    refreshStats();
    pollLatest();
  });

  // ─── Charts ───────────────────────────────────────────────────────────────
  const tickColor = "#94a3b8";
  const gridColor = "rgba(255,255,255,0.05)";

  function lineChart(canvas, label, color, opts = {}) {
    return new Chart(canvas, {
      type: "line",
      data: { labels: [], datasets: [{
        label, data: [], borderColor: color,
        backgroundColor: color + "1f",
        borderWidth: 2, pointRadius: 0, tension: 0.35, fill: true,
      }]},
      options: Object.assign({
        responsive: true, maintainAspectRatio: false, animation: false,
        scales: {
          x: { ticks: { color: tickColor, font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 8 }, grid: { color: gridColor } },
          y: { ticks: { color: tickColor, font: { family: "JetBrains Mono", size: 10 } }, grid: { color: gridColor } },
        },
        plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
      }, opts),
    });
  }

  function sparkChart(canvas, color) {
    return new Chart(canvas, {
      type: "line",
      data: { labels: [], datasets: [{
        data: [], borderColor: color, backgroundColor: color + "33",
        borderWidth: 1.6, pointRadius: 0, tension: 0.4, fill: true,
      }]},
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        scales: { x: { display: false }, y: { display: false } },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        elements: { line: { borderJoinStyle: "round" } },
      },
    });
  }

  const gasChart  = lineChart($("chart-gas"),  "Gas (ppm)",  "#38bdf8");
  const riskChart = lineChart($("chart-risk"), "Risk Score", "#a78bfa", {
    scales: { y: { min: 0, max: 1, ticks: { color: tickColor, font: { family: "JetBrains Mono", size: 10 } }, grid: { color: gridColor } },
              x: { ticks: { color: tickColor, font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 8 }, grid: { color: gridColor } } },
  });

  const thChart = new Chart($("chart-th"), {
    type: "line",
    data: { labels: [], datasets: [
      { label: "Temp (°C)", data: [], borderColor: "#fb923c", backgroundColor: "#fb923c22", borderWidth: 2, pointRadius: 0, tension: 0.3, yAxisID: "y" },
      { label: "Humidity (%)", data: [], borderColor: "#22d3ee", backgroundColor: "#22d3ee22", borderWidth: 2, pointRadius: 0, tension: 0.3, yAxisID: "y1" },
    ]},
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: {
        x:  { ticks: { color: tickColor, font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 8 }, grid: { color: gridColor } },
        y:  { position: "left",  ticks: { color: "#fb923c", font: { family: "JetBrains Mono", size: 10 } }, grid: { color: gridColor } },
        y1: { position: "right", ticks: { color: "#22d3ee", font: { family: "JetBrains Mono", size: 10 } }, grid: { display: false } },
      },
      plugins: { legend: { labels: { color: "#cbd5e1", font: { family: "Inter", size: 11 } } } },
    },
  });

  const sparkGas  = sparkChart($("spark-gas"),  "#38bdf8");
  const sparkTemp = sparkChart($("spark-temp"), "#fb923c");
  const sparkHum  = sparkChart($("spark-hum"),  "#22d3ee");

  let riskHistChart = null;
  let labelPieChart = null;

  function pushPoint(chart, label, datasetValues, max = MAX_CHART_PTS) {
    chart.data.labels.push(label);
    chart.data.datasets.forEach((ds, i) => ds.data.push(datasetValues[i]));
    if (chart.data.labels.length > max) {
      chart.data.labels.shift();
      chart.data.datasets.forEach(ds => ds.data.shift());
    }
    chart.update("none");
  }

  function pushSpark(chart, value, max = 30) {
    chart.data.labels.push("");
    chart.data.datasets[0].data.push(value);
    if (chart.data.labels.length > max) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    chart.update("none");
  }

  // ─── Gauge ────────────────────────────────────────────────────────────────
  const GAUGE_LEN = 172.8;
  function setGauge(score, label) {
    const arc = $("gauge-arc"), val = $("gauge-value"), card = $("stat-risk"), badge = $("risk-label");
    const meta = RISK_META[label] || RISK_META.NORMAL;
    const offset = GAUGE_LEN * (1 - Math.min(Math.max(score, 0), 1));
    arc.style.strokeDashoffset = offset;
    arc.style.stroke = meta.hex;
    val.textContent  = score.toFixed(4);
    val.style.color  = meta.hex;
    card.dataset.risk = label;
    badge.className   = "badge badge--label " + meta.cls;
    badge.textContent = label;
  }

  // ─── KPI updater ─────────────────────────────────────────────────────────
  function updateKpis(d) {
    $("kpi-gas-val").textContent  = fmt(d.gasPpm, 1);
    $("kpi-temp-val").textContent = fmt(d.temperatureC, 1);
    $("kpi-hum-val").textContent  = fmt(d.humidityPercent, 1);

    $("kpi-gas-sub").textContent  = `${d.deviceId || "—"} · ${fmtTime(d.ts)}`;
    // textContent above already escapes, no esc() needed.
    $("kpi-temp-sub").textContent = `Indoor sensor reading`;
    $("kpi-hum-sub").textContent  = `Relative humidity`;

    const gas = d.gasPpm ?? 0;
    const card = $("kpi-gas");
    card.classList.toggle("stat-card--danger", gas > thresholds.gasPpmAlert);
    card.classList.toggle("stat-card--warn",   gas > thresholds.gasPpmWarning && gas <= thresholds.gasPpmAlert);

    pushSpark(sparkGas,  gas);
    pushSpark(sparkTemp, d.temperatureC ?? 0);
    pushSpark(sparkHum,  d.humidityPercent ?? 0);

    const pipe = $("badge-pipeline");
    pipe.className   = "badge badge--system badge--normal";
    pipe.textContent = "● live";
  }

  // ─── Boot history ────────────────────────────────────────────────────────
  async function bootHistory() {
    try {
      const url = `${API}/dashboard/history?minutes=${state.rangeMins}&sample_every=${sampleEvery()}`
        + (state.deviceId ? `&device_id=${encodeURIComponent(state.deviceId)}` : "");
      const r = await fetch(url);
      const rows = await r.json();
      state.history = rows;

      gasChart.data.labels  = [];  gasChart.data.datasets[0].data  = [];
      riskChart.data.labels = []; riskChart.data.datasets[0].data = [];
      thChart.data.labels   = []; thChart.data.datasets.forEach(d => d.data = []);

      rows.forEach(r => {
        const t = fmtTime(r.ts);
        gasChart.data.labels.push(t);   gasChart.data.datasets[0].data.push(r.gasPpm);
        riskChart.data.labels.push(t);  riskChart.data.datasets[0].data.push(r.lstmRiskScore);
        thChart.data.labels.push(t);
        thChart.data.datasets[0].data.push(r.temperatureC);
        thChart.data.datasets[1].data.push(r.humidityPercent);
      });
      gasChart.update("none"); riskChart.update("none"); thChart.update("none");
    } catch (err) {
      console.warn("[history] failed", err);
    }
  }

  function sampleEvery() {
    if (state.rangeMins <= 30)  return 10;
    if (state.rangeMins <= 60)  return 30;
    if (state.rangeMins <= 360) return 120;
    return 300;
  }

  // ─── Poll latest ─────────────────────────────────────────────────────────
  async function pollLatest() {
    try {
      const url = `${API}/dashboard/latest`
        + (state.deviceId ? `?device_id=${encodeURIComponent(state.deviceId)}` : "");
      const r = await fetch(url);
      const d = await r.json();
      if (!r.ok || d.gasPpm === undefined) return;

      const t = fmtTime(d.ts);
      updateKpis(d);
      setGauge(d.lstmRiskScore ?? 0, d.riskLabel ?? "NORMAL");
      pushPoint(gasChart,  t, [d.gasPpm]);
      pushPoint(riskChart, t, [d.lstmRiskScore]);
      pushPoint(thChart,   t, [d.temperatureC, d.humidityPercent]);
      state.history.push(d);
      if (state.history.length > 1000) state.history.shift();
    } catch {
      const pipe = $("badge-pipeline");
      pipe.className   = "badge badge--system badge--alert";
      pipe.textContent = "● disconnected";
    }
  }

  // ─── Stats ────────────────────────────────────────────────────────────────
  async function refreshStats() {
    try {
      const url = `${API}/dashboard/stats?minutes=${state.rangeMins}`
        + (state.deviceId ? `&device_id=${encodeURIComponent(state.deviceId)}` : "");
      const r = await fetch(url);
      const s = await r.json();
      $("stat-avg-ppm").textContent  = fmt(s.avgPpm, 1);
      $("stat-max-ppm").textContent  = fmt(s.maxPpm, 1);
      $("stat-avg-risk").textContent = fmt(s.avgRiskScore, 4);

      $("an-count").textContent = s.count ?? "—";
      $("an-min").textContent   = fmt(s.minPpm, 1);
      $("an-avg").textContent   = fmt(s.avgPpm, 1);
      $("an-max").textContent   = fmt(s.maxPpm, 1);
      $("an-risk").textContent  = fmt(s.avgRiskScore, 4);
    } catch {/* ignore */}
  }

  // ─── Overview / pipeline ─────────────────────────────────────────────────
  async function pollOverview() {
    try {
      const r = await fetch(`${API}/dashboard/overview`);
      const d = await r.json();
      if (d.thresholds) thresholds = d.thresholds;
      const steps = { mqtt: "ps-mqtt", kafka: "ps-kafka", spark: "ps-spark", influxdb: "ps-influx" };
      Object.entries(steps).forEach(([svc, id]) => {
        const el  = $(id);  if (!el) return;
        const dot = el.querySelector(".pipeline-step__dot");
        const up  = d.services?.[svc] === "up";
        dot.classList.toggle("pipeline-step__dot--up",   up);
        dot.classList.toggle("pipeline-step__dot--down", !up);
      });
      const lstmDot = document.querySelector("#ps-lstm .pipeline-step__dot");
      if (lstmDot) lstmDot.classList.add("pipeline-step__dot--up");
    } catch {/* ignore */}
  }

  // ─── Devices ─────────────────────────────────────────────────────────────
  async function refreshDevices() {
    try {
      const r = await fetch(`${API}/devices`);
      const list = await r.json();

      // Update device select
      const sel = $("device-select");
      const cur = sel.value;
      sel.innerHTML = `<option value="">All devices</option>` +
        list.map(d => `<option value="${esc(d.deviceId)}">${esc(d.deviceId)}${d.location ? " — " + esc(d.location) : ""}</option>`).join("");
      sel.value = cur;

      $("stat-devices-online").textContent = list.filter(d => d.status === "online").length;
      $("devices-count").textContent       = `${list.length} total`;

      const grid = $("device-grid");
      if (list.length === 0) {
        grid.innerHTML = `<div class="device-grid__empty">No devices reporting.</div>`;
        return;
      }
      grid.innerHTML = list.map(d => {
        const meta = RISK_META[d.lastLabel] || RISK_META.NORMAL;
        const status = d.status === "online" ? "online" : "offline";
        return `
          <div class="device-card device-card--${status}">
            <div class="device-card__head">
              <div class="device-card__name">${esc(d.deviceId)}</div>
              <div class="device-card__status">${status === "online" ? "🟢 online" : "⚪ offline"}</div>
            </div>
            <div class="device-card__location">${esc(d.location || "Unknown location")}</div>
            <div class="device-card__metrics">
              <div><span>${fmt(d.lastPpm, 1)}</span><label>ppm</label></div>
              <div><span style="color:${meta.hex}">${fmt(d.lastRisk, 3)}</span><label>risk</label></div>
              <div><span class="badge ${meta.cls}">${esc(d.lastLabel || "—")}</span></div>
            </div>
            <div class="device-card__foot">${d.lastSeen ? "Last seen " + esc(fmtTime(d.lastSeen)) : "Never seen"}</div>
          </div>`;
      }).join("");
    } catch (err) {
      console.warn("[devices] failed", err);
    }
  }

  // ─── Alerts ──────────────────────────────────────────────────────────────
  async function refreshAlertsTable() {
    try {
      const r = await fetch(`${API}/alerts?hours=24&limit=200`);
      const list = await r.json();
      state.alerts = list;
      $("alerts-count").textContent = list.length;

      const stats = await fetch(`${API}/alerts/stats?hours=24`).then(x => x.json()).catch(() => null);
      if (stats) $("stat-alerts-24h").textContent = stats.total;

      const tbody = $("alerts-tbody");
      if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="alerts-table__empty">No alerts in the last 24 hours.</td></tr>`;
        return;
      }
      tbody.innerHTML = list.map(a => {
        const meta = RISK_META[a.riskLabel] || RISK_META.NORMAL;
        return `<tr>
          <td class="mono">${esc(fmtTime(a.eventTs))}</td>
          <td>${esc(a.deviceId)}</td>
          <td><span class="badge ${meta.cls}">${esc(a.riskLabel)}</span></td>
          <td class="num mono">${fmt(a.gasPpm, 1)}</td>
          <td class="num mono">${fmt(a.riskScore, 4)}</td>
          <td>${a.acknowledged ? "✓ acked" : `<button class="btn btn--ghost" data-ack="${esc(a.id)}">Ack</button>`}</td>
        </tr>`;
      }).join("");

      tbody.querySelectorAll("[data-ack]").forEach(btn => {
        btn.addEventListener("click", async () => {
          const id = btn.dataset.ack;
          await fetch(`${API}/alerts/${id}/ack`, { method: "POST" });
          refreshAlertsTable();
        });
      });
    } catch (err) {
      console.warn("[alerts] failed", err);
    }
  }

  function appendAlertFeed(a) {
    const list = $("alert-list");
    const empty = list.querySelector(".alert-list__empty");
    if (empty) empty.remove();

    const meta = RISK_META[a.riskLabel] || RISK_META.NORMAL;
    const li   = document.createElement("li");
    const labelKey = (a.riskLabel || "normal").toLowerCase().replace(/[^a-z]/g, "");
    li.className = "alert-item alert-item--" + labelKey;
    li.innerHTML = `
      <span class="alert-item__dot" style="background:${meta.hex}"></span>
      <span class="alert-item__body">
        <strong>${esc(a.riskLabel)}</strong> · ${esc(a.deviceId)}<br/>
        <span class="mono">${fmt(a.gasPpm, 1)} ppm · risk ${fmt(a.riskScore, 4)}</span>
      </span>
      <span class="alert-item__time">${esc(fmtTime(a.eventTs))}</span>`;
    list.prepend(li);
    while (list.children.length > 20) list.lastChild.remove();

    $("stat-risk").classList.add("stat-card--flash");
    setTimeout(() => $("stat-risk").classList.remove("stat-card--flash"), 600);

    if (a.riskLabel === "ALERT") toast(`🚨 ALERT — ${a.deviceId} at ${fmt(a.gasPpm, 0)} ppm`, "alert");
  }

  // ─── SSE alert stream ─────────────────────────────────────────────────────
  let sseBackoff = 2000;
  function initSSE() {
    try {
      const sse = new EventSource(`${API}/dashboard/alerts/stream`);
      sse.onopen    = () => { sseBackoff = 2000; };
      sse.onmessage = safe((e) => appendAlertFeed(JSON.parse(e.data)));
      sse.onerror   = () => {
        sse.close();
        setTimeout(initSSE, sseBackoff);
        sseBackoff = Math.min(sseBackoff * 2, 60_000);
      };
    } catch {
      console.warn("[SSE] EventSource not available");
    }
  }

  // ─── Analytics view (renders on tab switch + on stats refresh) ───────────
  function renderAnalytics() {
    const rows = state.history.slice(-MAX_CHART_PTS * 4);
    if (rows.length === 0) return;

    // histogram of risk scores into 10 bins
    const bins = new Array(10).fill(0);
    rows.forEach(r => {
      const idx = Math.min(9, Math.max(0, Math.floor((r.lstmRiskScore || 0) * 10)));
      bins[idx]++;
    });
    const labels = bins.map((_, i) => `${(i/10).toFixed(1)}-${((i+1)/10).toFixed(1)}`);

    if (!riskHistChart) {
      riskHistChart = new Chart($("chart-risk-hist"), {
        type: "bar",
        data: { labels, datasets: [{ label: "Samples", data: bins, backgroundColor: "#a78bfa", borderRadius: 4 }] },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false,
          scales: {
            x: { ticks: { color: tickColor, font: { family: "JetBrains Mono", size: 10 } }, grid: { color: gridColor } },
            y: { ticks: { color: tickColor, font: { family: "JetBrains Mono", size: 10 } }, grid: { color: gridColor } },
          },
          plugins: { legend: { display: false } },
        },
      });
    } else {
      riskHistChart.data.labels = labels;
      riskHistChart.data.datasets[0].data = bins;
      riskHistChart.update("none");
    }

    const counts = { NORMAL: 0, WARNING: 0, ALERT: 0 };
    rows.forEach(r => { counts[r.riskLabel] = (counts[r.riskLabel] || 0) + 1; });
    const pieData = [counts.NORMAL, counts.WARNING, counts.ALERT];

    if (!labelPieChart) {
      labelPieChart = new Chart($("chart-label-pie"), {
        type: "doughnut",
        data: {
          labels: ["NORMAL", "WARNING", "ALERT"],
          datasets: [{ data: pieData, backgroundColor: ["#22c55e", "#f59e0b", "#ef4444"], borderColor: "#0a0f1e", borderWidth: 2 }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false, cutout: "62%",
          plugins: { legend: { labels: { color: "#cbd5e1", font: { family: "Inter", size: 11 } } } },
        },
      });
    } else {
      labelPieChart.data.datasets[0].data = pieData;
      labelPieChart.update("none");
    }
  }

  // ─── Boot sequence ───────────────────────────────────────────────────────
  bootHistory();
  pollLatest();      setInterval(pollLatest,    POLL_LATEST_MS);
  pollOverview();    setInterval(pollOverview,  POLL_OVERVIEW_MS);
  refreshStats();    setInterval(refreshStats,  POLL_OVERVIEW_MS);
  refreshDevices();  setInterval(refreshDevices, POLL_DEVICES_MS);
  refreshAlertsTable(); setInterval(refreshAlertsTable, POLL_ALERTS_MS);
  initSSE();
})();
