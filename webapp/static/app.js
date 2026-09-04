/* =============================================================
   CryptoLab · Lógica del Frontend (Vanilla JS + Plotly.js)
   Arquitectura modular e independiente por pestaña:
   - Tab 1: Backtesting Direccional (Scalping 1h & Tendencia Diario)
   - Tab 2: Bot de Malla / Grid (Goteo de Micro-Ganancias)
   ============================================================= */

(function () {
  "use strict";

  /* ── Paleta de Colores Compartida (Sincronizada con style.css) ── */
  var C = {
    text:      "#e9edf6",
    dim:       "#aab4c8",
    faint:     "#7c879d", /* Cumple 4.5:1 WCAG AA sobre fondos oscuros */
    grid:      "rgba(255, 255, 255, 0.06)",
    axis:      "rgba(255, 255, 255, 0.12)",
    surface:   "#161a27",
    close:     "#cbd5e1",
    fastMa:    "#fbbf24",
    slowMa:    "#7c6bff",
    entry:     "#34d399",
    exitSig:   "#60a5fa",
    exitStop:  "#fb7185",
    exitEnd:   "#94a3b8",
    gridLine:  "rgba(124, 107, 255, 0.3)",
    gridSell:  "#38bdf8"
  };

  var SANS = '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  var MONO = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';

  var PLOT_CONFIG = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["select2d", "lasso2d", "toggleSpikelines"],
    toImageButtonOptions: { format: "png", scale: 2 }
  };

  /* ── Utilidades de Formateo ─────────────────────────────────── */
  function $(id) {
    return document.getElementById(id);
  }

  function isNum(v) {
    return typeof v === "number" && isFinite(v);
  }

  function fmtPct(v, decimals) {
    if (!isNum(v)) { return "—"; }
    var d = typeof decimals === "number" ? decimals : 1;
    return (v * 100).toFixed(d) + "%";
  }

  function fmtSignedPct(v, decimals) {
    if (!isNum(v)) { return "—"; }
    var out = fmtPct(v, decimals);
    return v > 0 ? "+" + out : out;
  }

  function fmtNum(v, decimals) {
    if (!isNum(v)) { return "—"; }
    return v.toFixed(typeof decimals === "number" ? decimals : 2);
  }

  function priceDecimals(v) {
    var abs = Math.abs(v);
    if (abs >= 1000) { return 2; }
    if (abs >= 1) { return 2; }
    if (abs >= 0.01) { return 4; }
    return 6;
  }

  function fmtPrice(v) {
    if (!isNum(v)) { return "—"; }
    var d = priceDecimals(v);
    return "$" + v.toLocaleString("en-US", {
      minimumFractionDigits: d,
      maximumFractionDigits: d
    });
  }

  function fmtMoney(v) {
    if (!isNum(v)) { return "—"; }
    return "$" + v.toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
  }

  function fmtQty(v) {
    if (!isNum(v)) { return "—"; }
    if (Math.abs(v) >= 100) { return v.toFixed(2); }
    if (Math.abs(v) >= 1) { return v.toFixed(4); }
    return v.toFixed(6);
  }

  function signClass(v) {
    if (!isNum(v) || v === 0) { return ""; }
    return v > 0 ? "is-pos" : "is-neg";
  }

  function quietSignClass(v) {
    if (!isNum(v) || v === 0) { return ""; }
    return v > 0 ? "is-quiet-pos" : "is-quiet-neg";
  }

  function cellText(text, cls) {
    var td = document.createElement("td");
    td.textContent = text == null ? "—" : text;
    if (cls) { td.className = cls.trim(); }
    return td;
  }

  function explainedError(msg) {
    var err = new Error(msg);
    err.explained = true;
    return err;
  }

  /* ── Layout Base para Gráficas Plotly ───────────────────────── */
  function baseLayout() {
    return {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: SANS, size: 12, color: C.dim },
      margin: { l: 68, r: 24, t: 14, b: 46 },
      hovermode: "x unified",
      hoverlabel: {
        bgcolor: C.surface,
        bordercolor: "rgba(255,255,255,.16)",
        font: { family: MONO, size: 12, color: C.text }
      },
      xaxis: {
        type: "date",
        gridcolor: C.grid,
        zeroline: false,
        linecolor: C.axis,
        tickfont: { family: MONO, size: 11, color: C.faint },
        showspikes: true,
        spikemode: "across",
        spikethickness: 1,
        spikedash: "dot",
        spikecolor: "rgba(255,255,255,.25)"
      },
      yaxis: {
        gridcolor: C.grid,
        zeroline: false,
        linecolor: "rgba(0,0,0,0)",
        tickfont: { family: MONO, size: 11, color: C.faint }
      },
      legend: {
        orientation: "h",
        yanchor: "bottom",
        y: 1.02,
        xanchor: "left",
        x: 0,
        bgcolor: "rgba(0,0,0,0)",
        font: { size: 11.5, color: C.dim }
      },
      modebar: {
        bgcolor: "rgba(0,0,0,0)",
        color: C.faint,
        activecolor: C.text
      }
    };
  }

  /* ═══════════════════════════════════════════════════════════════
     TAB 1: CONTROLADOR DE BACKTESTING (SCALPING / TENDENCIA)
     ═══════════════════════════════════════════════════════════════ */
  var btTab = {
    running: false,
    chartsDrawn: false,
    timerId: null,

    dom: {
      symbol:       $("bt-symbol"),
      strategy:     $("bt-strategy"),
      runBtn:       $("bt-run"),
      errorBanner:  $("bt-error"),
      errorMessage: $("bt-error-message"),
      errorDismiss: $("bt-error-dismiss"),
      emptyState:   $("bt-empty"),
      loadingState: $("bt-loading"),
      loadingSym:   $("bt-loading-symbol"),
      loadingTimer: $("bt-loading-timer"),
      results:      $("bt-results"),
      resultsSym:   $("bt-results-symbol"),
      resultsMeta:  $("bt-results-meta"),
      paramsList:   $("bt-params"),
      mTotalReturn: $("bt-m-total-return"),
      mWinRate:     $("bt-m-win-rate"),
      mMaxDrawdown: $("bt-m-max-drawdown"),
      mSharpe:      $("bt-m-sharpe"),
      mNumTrades:   $("bt-m-num-trades"),
      chartPrice:   $("bt-chart-price"),
      chartEquity:  $("bt-chart-equity"),
      tradesCount:  $("bt-trades-count"),
      tradesBody:   $("bt-trades-body")
    },

    showError: function (msg) {
      this.dom.errorMessage.textContent = msg;
      this.dom.errorBanner.hidden = false;
    },

    hideError: function () {
      this.dom.errorBanner.hidden = true;
      this.dom.errorMessage.textContent = "";
    },

    clearResults: function () {
      this.dom.results.hidden = true;
      if (this.chartsDrawn && window.Plotly) {
        window.Plotly.purge(this.dom.chartPrice);
        window.Plotly.purge(this.dom.chartEquity);
        this.chartsDrawn = false;
      }
      this.dom.tradesBody.innerHTML = "";
      this.dom.paramsList.innerHTML = "";

      this.dom.mTotalReturn.textContent = "—";
      this.dom.mTotalReturn.className = "metric__value";
      this.dom.mWinRate.textContent = "—";
      this.dom.mWinRate.className = "metric__value";
      this.dom.mMaxDrawdown.textContent = "—";
      this.dom.mMaxDrawdown.className = "metric__value";
      this.dom.mSharpe.textContent = "—";
      this.dom.mSharpe.className = "metric__value";
      this.dom.mNumTrades.textContent = "—";
      this.dom.mNumTrades.className = "metric__value";
    },

    startTimer: function () {
      var self = this;
      var t0 = Date.now();
      self.dom.loadingTimer.textContent = "0.0s";
      self.stopTimer();
      self.timerId = window.setInterval(function () {
        self.dom.loadingTimer.textContent = ((Date.now() - t0) / 1000).toFixed(1) + "s";
      }, 100);
    },

    stopTimer: function () {
      if (this.timerId !== null) {
        window.clearInterval(this.timerId);
        this.timerId = null;
      }
    },

    setBusy: function (busy, symbol) {
      this.running = busy;
      this.dom.runBtn.disabled = busy;
      this.dom.symbol.disabled = busy;
      this.dom.strategy.disabled = busy;
      this.dom.runBtn.classList.toggle("is-busy", busy);
      this.dom.runBtn.setAttribute("aria-busy", busy ? "true" : "false");
      this.dom.runBtn.querySelector(".btn__label").textContent = busy ? "Corriendo…" : "Correr backtest";

      if (busy) {
        this.dom.loadingSym.textContent = symbol || "—";
        this.dom.loadingState.hidden = false;
        this.dom.emptyState.hidden = true;
        this.startTimer();
      } else {
        this.dom.loadingState.hidden = true;
        this.stopTimer();
      }
    },

    run: function () {
      var self = this;
      if (self.running) { return; }

      var symbol = self.dom.symbol.value;
      var strat = self.dom.strategy.value;
      if (!symbol) {
        self.showError("Por favor selecciona un símbolo para el backtest.");
        return;
      }

      self.hideError();
      self.clearResults();
      self.setBusy(true, symbol);

      var payload = {
        symbol: symbol,
        strategy_type: strat,
        timeframe: strat === "scalping_1h" ? "1h" : "1d"
      };

      fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(function (res) {
          return res.json().then(
            function (body) { return { ok: res.ok, status: res.status, body: body }; },
            function () { return { ok: res.ok, status: res.status, body: null }; }
          );
        })
        .then(function (result) {
          if (!result.ok) {
            var detail = result.body && result.body.detail;
            throw explainedError(detail || ("El servidor respondió con código " + result.status));
          }
          if (!result.body) {
            throw explainedError("La respuesta del servidor no es JSON válido.");
          }
          self.setBusy(false);
          self.render(result.body);
        })
        .catch(function (err) {
          self.setBusy(false);
          self.clearResults();
          self.dom.emptyState.hidden = true;
          self.showError(err && err.explained
            ? err.message
            : "No se pudo conectar con el servidor. Verifica que esté activo en http://127.0.0.1:8000.");
        });
    },

    render: function (data) {
      if (!window.Plotly) {
        throw explainedError("Plotly.js no está cargado. Revisa tu conexión a internet.");
      }

      this.hideError();
      this.dom.emptyState.hidden = true;

      this.renderParams(data.params || {});
      this.renderHeader(data);
      this.renderMetrics(data.metrics || {});
      this.renderTrades(data.trades || []);

      this.dom.results.hidden = false;

      this.renderPriceChart(data);
      this.renderEquityChart(data);
      this.chartsDrawn = true;
    },

    renderParams: function (p) {
      this.dom.paramsList.innerHTML = "";
      var items = [];
      if (p.fast_window) { items.push({ label: "MA Rápida", val: String(p.fast_window) }); }
      if (p.slow_window) { items.push({ label: "MA Lenta", val: String(p.slow_window) }); }
      if (p.stop_loss_pct !== undefined) { items.push({ label: "Stop-Loss", val: fmtPct(p.stop_loss_pct, 1) }); }
      if (p.initial_capital) { items.push({ label: "Capital", val: fmtMoney(p.initial_capital) }); }
      if (p.timeframe) { items.push({ label: "Temporalidad", val: p.timeframe }); }

      var self = this;
      items.forEach(function (it) {
        var div = document.createElement("div");
        div.className = "params__item";
        div.innerHTML = "<dt>" + it.label + "</dt><dd>" + it.val + "</dd>";
        self.dom.paramsList.appendChild(div);
      });
    },

    renderHeader: function (data) {
      var dates = data.dates || [];
      this.dom.resultsSym.textContent = data.symbol || "—";

      var parts = [];
      if (dates.length) {
        parts.push(dates[0] + " → " + dates[dates.length - 1]);
        var is1h = data.params && data.params.timeframe === "1h";
        parts.push(dates.length + (is1h ? " velas de 1h" : " velas diarias"));
      }
      var eq = data.equity_curve || [];
      var last = eq.length ? eq[eq.length - 1] : null;
      if (isNum(last)) {
        parts.push("Equity final " + fmtMoney(last));
      }
      this.dom.resultsMeta.textContent = parts.join("  ·  ") || "—";
    },

    renderMetrics: function (m) {
      // 1. Retorno Total
      this.dom.mTotalReturn.textContent = fmtSignedPct(m.total_return, 1);
      this.dom.mTotalReturn.className = "metric__value " + signClass(m.total_return);

      // 2. Win Rate
      this.dom.mWinRate.textContent = fmtPct(m.win_rate, 1);
      this.dom.mWinRate.className = "metric__value";

      // 3. Max Drawdown
      this.dom.mMaxDrawdown.textContent = fmtPct(m.max_drawdown, 1);
      this.dom.mMaxDrawdown.className = "metric__value is-risk";

      // 4. Sharpe Ratio
      this.dom.mSharpe.textContent = fmtNum(m.sharpe_ratio, 2);
      this.dom.mSharpe.className = "metric__value " + quietSignClass(m.sharpe_ratio);

      // 5. Total Trades
      this.dom.mNumTrades.textContent = isNum(m.num_trades) ? String(Math.round(m.num_trades)) : "0";
      this.dom.mNumTrades.className = "metric__value";
    },

    renderTrades: function (trades) {
      this.dom.tradesBody.innerHTML = "";
      this.dom.tradesCount.textContent = trades.length
        ? trades.length + (trades.length === 1 ? " operación" : " operaciones")
        : "Sin operaciones ejecutadas";

      if (!trades.length) {
        var emptyRow = document.createElement("tr");
        emptyRow.className = "empty-row";
        emptyRow.innerHTML = '<td colspan="6">La estrategia no abrió posiciones en el periodo seleccionado.</td>';
        this.dom.tradesBody.appendChild(emptyRow);
        return;
      }

      var REASON_LABEL = { signal: "Señal", stop_loss: "Stop-loss", end_of_data: "Fin datos" };
      var REASON_TAG = { signal: "tag--signal", stop_loss: "tag--stop", end_of_data: "tag--end" };

      var self = this;
      trades.slice().reverse().forEach(function (t) {
        var tr = document.createElement("tr");
        tr.appendChild(cellText(t.entry_date, "date"));
        tr.appendChild(cellText(t.exit_date, "date"));
        tr.appendChild(cellText(fmtPrice(t.entry_price), "num"));
        tr.appendChild(cellText(fmtPrice(t.exit_price), "num"));
        tr.appendChild(cellText(fmtSignedPct(t.pnl_pct, 2), "num pnl " + signClass(t.pnl_pct)));

        var tdReason = document.createElement("td");
        var tag = document.createElement("span");
        var tagCls = REASON_TAG[t.exit_reason] || "tag--end";
        tag.className = "tag " + tagCls;
        tag.textContent = REASON_LABEL[t.exit_reason] || t.exit_reason || "—";
        tdReason.appendChild(tag);
        tr.appendChild(tdReason);

        self.dom.tradesBody.appendChild(tr);
      });
    },

    renderPriceChart: function (data) {
      var dates = data.dates || [];
      var trades = data.trades || [];
      var params = data.params || {};

      var fastName = "MA " + (params.fast_window || 20);
      var slowName = "MA " + (params.slow_window || 50);

      var traces = [
        {
          type: "scatter",
          mode: "lines",
          name: "Cierre",
          x: dates,
          y: data.close || [],
          line: { color: C.close, width: 1.5 },
          connectgaps: false,
          hovertemplate: "%{x}<br>Precio: $%{y:,.4~f}<extra>Cierre</extra>"
        },
        {
          type: "scatter",
          mode: "lines",
          name: fastName,
          x: dates,
          y: data.fast_ma || [],
          line: { color: C.fastMa, width: 1.8 },
          connectgaps: false,
          hovertemplate: fastName + ": $%{y:,.4~f}<extra></extra>"
        },
        {
          type: "scatter",
          mode: "lines",
          name: slowName,
          x: dates,
          y: data.slow_ma || [],
          line: { color: C.slowMa, width: 1.8 },
          connectgaps: false,
          hovertemplate: slowName + ": $%{y:,.4~f}<extra></extra>"
        }
      ];

      var entryX = [], entryY = [], entryMeta = [];
      var exitSigX = [], exitSigY = [], exitSigMeta = [];
      var exitStopX = [], exitStopY = [], exitStopMeta = [];
      var exitEndX = [], exitEndY = [], exitEndMeta = [];

      trades.forEach(function (t) {
        entryX.push(t.entry_date);
        entryY.push(t.entry_price);
        entryMeta.push([fmtPrice(t.entry_price)]);

        if (t.exit_reason === "signal") {
          exitSigX.push(t.exit_date);
          exitSigY.push(t.exit_price);
          exitSigMeta.push([fmtPrice(t.exit_price), fmtSignedPct(t.pnl_pct, 2)]);
        } else if (t.exit_reason === "stop_loss") {
          exitStopX.push(t.exit_date);
          exitStopY.push(t.exit_price);
          exitStopMeta.push([fmtPrice(t.exit_price), fmtSignedPct(t.pnl_pct, 2)]);
        } else {
          exitEndX.push(t.exit_date);
          exitEndY.push(t.exit_price);
          exitEndMeta.push([fmtPrice(t.exit_price), fmtSignedPct(t.pnl_pct, 2)]);
        }
      });

      if (entryX.length) {
        traces.push({
          type: "scatter",
          mode: "markers",
          name: "Entrada Long",
          x: entryX,
          y: entryY,
          customdata: entryMeta,
          marker: { color: C.entry, size: 9, symbol: "triangle-up", line: { color: "#0c0a17", width: 1.2 } },
          hovertemplate: "<b>Entrada</b><br>Precio: %{customdata[0]}<extra></extra>"
        });
      }

      if (exitSigX.length) {
        traces.push({
          type: "scatter",
          mode: "markers",
          name: "Salida Señal",
          x: exitSigX,
          y: exitSigY,
          customdata: exitSigMeta,
          marker: { color: C.exitSig, size: 9, symbol: "triangle-down", line: { color: "#0c0a17", width: 1.2 } },
          hovertemplate: "<b>Salida Señal</b><br>Precio: %{customdata[0]}<br>P&L: %{customdata[1]}<extra></extra>"
        });
      }

      if (exitStopX.length) {
        traces.push({
          type: "scatter",
          mode: "markers",
          name: "Salida Stop-Loss",
          x: exitStopX,
          y: exitStopY,
          customdata: exitStopMeta,
          marker: { color: C.exitStop, size: 9, symbol: "x", line: { color: "#0c0a17", width: 1.5 } },
          hovertemplate: "<b>Salida Stop-Loss</b><br>Precio: %{customdata[0]}<br>P&L: %{customdata[1]}<extra></extra>"
        });
      }

      if (exitEndX.length) {
        traces.push({
          type: "scatter",
          mode: "markers",
          name: "Salida Fin Datos",
          x: exitEndX,
          y: exitEndY,
          customdata: exitEndMeta,
          marker: { color: C.exitEnd, size: 8, symbol: "circle-open", line: { color: C.exitEnd, width: 2 } },
          hovertemplate: "<b>Salida Fin Periodo</b><br>Precio: %{customdata[0]}<br>P&L: %{customdata[1]}<extra></extra>"
        });
      }

      var layout = baseLayout();
      layout.yaxis.title = { text: "Precio (USDT)", font: { family: SANS, size: 11.5, color: C.faint } };

      window.Plotly.react(this.dom.chartPrice, traces, layout, PLOT_CONFIG);
    },

    renderEquityChart: function (data) {
      var dates = data.dates || [];
      var equity = data.equity_curve || [];

      var start = null;
      for (var i = 0; i < equity.length; i++) {
        if (isNum(equity[i])) { start = equity[i]; break; }
      }
      var end = null;
      for (var j = equity.length - 1; j >= 0; j--) {
        if (isNum(equity[j])) { end = equity[j]; break; }
      }

      var up = isNum(start) && isNum(end) ? end >= start : true;
      var lineColor = up ? C.entry : C.exitStop;
      var fillColor = up ? "rgba(52, 211, 153, 0.12)" : "rgba(251, 113, 133, 0.12)";

      var traces = [{
        type: "scatter",
        mode: "lines",
        name: "Equity",
        x: dates,
        y: equity,
        line: { color: lineColor, width: 2, shape: "linear" },
        fill: "tozeroy",
        fillcolor: fillColor,
        connectgaps: false,
        hovertemplate: "%{x}<br>Equity: $%{y:,.2f}<extra>Capital</extra>"
      }];

      var layout = baseLayout();
      layout.showlegend = false;
      layout.margin.t = 16;
      layout.yaxis.title = { text: "Valor de la cuenta", font: { family: SANS, size: 11.5, color: C.faint } };
      layout.yaxis.tickprefix = "$";
      layout.yaxis.tickformat = ",.0f";

      var finite = equity.filter(isNum);
      if (finite.length) {
        var lo = Math.min.apply(null, finite);
        var hi = Math.max.apply(null, finite);
        var pad = (hi - lo) * 0.09;
        if (!(pad > 0)) { pad = Math.max(Math.abs(hi) * 0.05, 1); }
        layout.yaxis.range = [lo - pad, hi + pad];
      }

      if (isNum(start) && dates.length) {
        layout.shapes = [{
          type: "line",
          xref: "paper", x0: 0, x1: 1,
          yref: "y", y0: start, y1: start,
          line: { color: "rgba(255,255,255,0.25)", width: 1, dash: "dot" },
          layer: "below"
        }];
        layout.annotations = [{
          xref: "paper", x: 1, xanchor: "right",
          yref: "y", y: start, yanchor: "bottom",
          text: "Capital inicial " + fmtMoney(start),
          showarrow: false,
          font: { family: MONO, size: 10.5, color: C.faint }
        }];
      }

      window.Plotly.react(this.dom.chartEquity, traces, layout, PLOT_CONFIG);
    },

    resize: function () {
      if (this.chartsDrawn && window.Plotly) {
        window.Plotly.Plots.resize(this.dom.chartPrice);
        window.Plotly.Plots.resize(this.dom.chartEquity);
      }
    }
  };

  /* ═══════════════════════════════════════════════════════════════
     TAB 2: CONTROLADOR DEL BOT DE MALLA (GRID / GOTEO)
     ═══════════════════════════════════════════════════════════════ */
  var gridTab = {
    running: false,
    chartsDrawn: false,
    timerId: null,

    dom: {
      symbol:       $("grid-symbol"),
      numGrids:     $("grid-num"),
      lowerPrice:   $("grid-lower"),
      upperPrice:   $("grid-upper"),
      runBtn:       $("grid-run"),
      errorBanner:  $("grid-error"),
      errorMessage: $("grid-error-message"),
      errorDismiss: $("grid-error-dismiss"),
      emptyState:   $("grid-empty"),
      loadingState: $("grid-loading"),
      loadingSym:   $("grid-loading-symbol"),
      loadingTimer: $("grid-loading-timer"),
      results:      $("grid-results"),
      resultsSym:   $("grid-results-symbol"),
      resultsMeta:  $("grid-results-meta"),
      paramsList:   $("grid-params"),
      mRealized:    $("grid-m-realized"),
      mTotalReturn: $("grid-m-total-return"),
      mBuys:        $("grid-m-buys"),
      mSells:       $("grid-m-sells"),
      mStatus:      $("grid-m-status"),
      mStatusNote:  $("grid-m-status-note"),
      chartPrice:   $("grid-chart-price"),
      chartEquity:  $("grid-chart-equity"),
      tradesCount:  $("grid-trades-count"),
      tradesBody:   $("grid-trades-body")
    },

    showError: function (msg) {
      this.dom.errorMessage.textContent = msg;
      this.dom.errorBanner.hidden = false;
    },

    hideError: function () {
      this.dom.errorBanner.hidden = true;
      this.dom.errorMessage.textContent = "";
    },

    clearResults: function () {
      this.dom.results.hidden = true;
      if (this.chartsDrawn && window.Plotly) {
        window.Plotly.purge(this.dom.chartPrice);
        window.Plotly.purge(this.dom.chartEquity);
        this.chartsDrawn = false;
      }
      this.dom.tradesBody.innerHTML = "";
      this.dom.paramsList.innerHTML = "";

      this.dom.mRealized.textContent = "—";
      this.dom.mTotalReturn.textContent = "—";
      this.dom.mTotalReturn.className = "metric__value";
      this.dom.mBuys.textContent = "—";
      this.dom.mSells.textContent = "—";
      this.dom.mStatus.textContent = "—";
      this.dom.mStatus.className = "metric__value";
      this.dom.mStatusNote.textContent = "Posición actual vs rejilla";
    },

    startTimer: function () {
      var self = this;
      var t0 = Date.now();
      self.dom.loadingTimer.textContent = "0.0s";
      self.stopTimer();
      self.timerId = window.setInterval(function () {
        self.dom.loadingTimer.textContent = ((Date.now() - t0) / 1000).toFixed(1) + "s";
      }, 100);
    },

    stopTimer: function () {
      if (this.timerId !== null) {
        window.clearInterval(this.timerId);
        this.timerId = null;
      }
    },

    setBusy: function (busy, symbol) {
      this.running = busy;
      this.dom.runBtn.disabled = busy;
      this.dom.symbol.disabled = busy;
      this.dom.numGrids.disabled = busy;
      this.dom.lowerPrice.disabled = busy;
      this.dom.upperPrice.disabled = busy;
      this.dom.runBtn.classList.toggle("is-busy", busy);
      this.dom.runBtn.setAttribute("aria-busy", busy ? "true" : "false");
      this.dom.runBtn.querySelector(".btn__label").textContent = busy ? "Simulando…" : "Simular Malla";

      if (busy) {
        this.dom.loadingSym.textContent = symbol || "—";
        this.dom.loadingState.hidden = false;
        this.dom.emptyState.hidden = true;
        this.startTimer();
      } else {
        this.dom.loadingState.hidden = true;
        this.stopTimer();
      }
    },

    run: function () {
      var self = this;
      if (self.running) { return; }

      var symbol = self.dom.symbol.value;
      if (!symbol) {
        self.showError("Por favor selecciona un símbolo para la simulación de malla.");
        return;
      }

      var numGrids = parseInt(self.dom.numGrids.value, 10);
      if (isNaN(numGrids) || numGrids < 3 || numGrids > 50) {
        self.showError("El número de rejillas debe ser un entero entre 3 y 50.");
        return;
      }

      var lowerVal = parseFloat(self.dom.lowerPrice.value);
      var upperVal = parseFloat(self.dom.upperPrice.value);

      if (!isNaN(lowerVal) && !isNaN(upperVal) && lowerVal >= upperVal) {
        self.showError("El rango inferior (" + lowerVal + ") debe ser menor que el rango superior (" + upperVal + ").");
        return;
      }

      self.hideError();
      self.clearResults();
      self.setBusy(true, symbol);

      var payload = {
        symbol: symbol,
        num_grids: numGrids,
        timeframe: "1h"
      };

      if (!isNaN(lowerVal) && lowerVal > 0) {
        payload.lower_price = lowerVal;
      }
      if (!isNaN(upperVal) && upperVal > 0) {
        payload.upper_price = upperVal;
      }

      fetch("/api/backtest/grid", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(function (res) {
          return res.json().then(
            function (body) { return { ok: res.ok, status: res.status, body: body }; },
            function () { return { ok: res.ok, status: res.status, body: null }; }
          );
        })
        .then(function (result) {
          if (!result.ok) {
            var detail = result.body && result.body.detail;
            throw explainedError(detail || ("El servidor respondió con código " + result.status));
          }
          if (!result.body) {
            throw explainedError("La respuesta del servidor no es JSON válido.");
          }
          self.setBusy(false);
          self.render(result.body);
        })
        .catch(function (err) {
          self.setBusy(false);
          self.clearResults();
          self.dom.emptyState.hidden = true;
          self.showError(err && err.explained
            ? err.message
            : "No se pudo conectar con el servidor. Verifica que esté activo en http://127.0.0.1:8000.");
        });
    },

    render: function (data) {
      if (!window.Plotly) {
        throw explainedError("Plotly.js no está cargado. Revisa tu conexión a internet.");
      }

      this.hideError();
      this.dom.emptyState.hidden = true;

      this.renderParams(data.params || {}, data.grid_step);
      this.renderHeader(data);
      this.renderMetrics(data);
      this.renderTrades(data.trades || []);

      this.dom.results.hidden = false;

      this.renderPriceChart(data);
      this.renderEquityChart(data);
      this.chartsDrawn = true;
    },

    renderParams: function (p, gridStep) {
      this.dom.paramsList.innerHTML = "";
      var items = [];
      if (p.num_grids) { items.push({ label: "Rejillas", val: p.num_grids + " niveles" }); }
      if (p.lower_price) { items.push({ label: "Límite Inferior", val: fmtPrice(p.lower_price) }); }
      if (p.upper_price) { items.push({ label: "Límite Superior", val: fmtPrice(p.upper_price) }); }
      if (gridStep) { items.push({ label: "Paso de Malla", val: fmtPrice(gridStep) }); }
      if (p.initial_capital) { items.push({ label: "Capital Asignado", val: fmtMoney(p.initial_capital) }); }
      if (p.timeframe) { items.push({ label: "Velas", val: p.timeframe }); }

      var self = this;
      items.forEach(function (it) {
        var div = document.createElement("div");
        div.className = "params__item";
        div.innerHTML = "<dt>" + it.label + "</dt><dd>" + it.val + "</dd>";
        self.dom.paramsList.appendChild(div);
      });
    },

    renderHeader: function (data) {
      var dates = data.dates || [];
      this.dom.resultsSym.textContent = data.symbol || "—";

      var parts = [];
      if (dates.length) {
        parts.push(dates[0] + " → " + dates[dates.length - 1]);
        parts.push(dates.length + " velas de 1h");
      }
      var eq = data.equity_curve || [];
      var last = eq.length ? eq[eq.length - 1] : null;
      if (isNum(last)) {
        parts.push("Equity final " + fmtMoney(last));
      }
      this.dom.resultsMeta.textContent = parts.join("  ·  ") || "—";
    },

    renderMetrics: function (data) {
      var m = data.metrics || {};
      var p = data.params || {};

      // 1. Ganancia por Goteo (Beneficio Realizado en USDT, destacado en verde)
      var realized = isNum(m.realized_profit) ? m.realized_profit : 0;
      var sign = realized > 0 ? "+" : "";
      this.dom.mRealized.textContent = sign + fmtPrice(realized) + " USDT";

      // 2. Retorno Total (%)
      this.dom.mTotalReturn.textContent = fmtSignedPct(m.total_return, 2);
      this.dom.mTotalReturn.className = "metric__value " + signClass(m.total_return);

      // 3. Compras en Malla (contador)
      var numBuys = isNum(m.num_buys) ? m.num_buys : 0;
      this.dom.mBuys.textContent = String(numBuys);

      // 4. Ventas con Beneficio (contador)
      var numSells = isNum(m.num_sells) ? m.num_sells : 0;
      this.dom.mSells.textContent = String(numSells);

      // 5. Estado del Rango ('Dentro de rango' o 'Fuera de rango')
      var stopped = !!m.stopped_out;
      var close = data.close || [];
      var lastPrice = close.length ? close[close.length - 1] : null;
      var inRange = true;
      var note = "Precio activo dentro de los límites";

      if (stopped) {
        inRange = false;
        note = "Stop-loss de seguridad alcanzado";
      } else if (isNum(lastPrice) && isNum(p.lower_price) && isNum(p.upper_price)) {
        if (lastPrice < p.lower_price) {
          inRange = false;
          note = "Precio debajo del límite inferior";
        } else if (lastPrice > p.upper_price) {
          inRange = false;
          note = "Precio superó el límite superior";
        }
      }

      this.dom.mStatus.textContent = inRange ? "Dentro de rango" : "Fuera de rango";
      this.dom.mStatus.className = "metric__value " + (inRange ? "is-pos" : "is-risk");
      this.dom.mStatusNote.textContent = note;
    },

    renderTrades: function (trades) {
      this.dom.tradesBody.innerHTML = "";
      this.dom.tradesCount.textContent = trades.length
        ? trades.length + (trades.length === 1 ? " micro-operación" : " micro-operaciones")
        : "Sin micro-operaciones ejecutadas";

      if (!trades.length) {
        var emptyRow = document.createElement("tr");
        emptyRow.className = "empty-row";
        emptyRow.innerHTML = '<td colspan="5">La malla no ejecutó órdenes en este rango temporal.</td>';
        this.dom.tradesBody.appendChild(emptyRow);
        return;
      }

      var self = this;
      // Mostrar las operaciones más recientes arriba
      trades.slice(-80).reverse().forEach(function (t) {
        var tr = document.createElement("tr");

        // Fecha
        tr.appendChild(cellText(t.date, "date"));

        // Tipo (Compra / Venta / Stop-Loss)
        var tdType = document.createElement("td");
        var tag = document.createElement("span");
        if (t.type === "grid_buy") {
          tag.className = "tag tag--buy";
          tag.textContent = "Compra Malla";
        } else if (t.type === "grid_sell") {
          tag.className = "tag tag--sell";
          tag.textContent = "Venta Beneficio";
        } else {
          tag.className = "tag tag--stop";
          tag.textContent = "Stop-Loss Salida";
        }
        tdType.appendChild(tag);
        tr.appendChild(tdType);

        // Precio
        tr.appendChild(cellText(fmtPrice(t.price), "num"));

        // Cantidad
        tr.appendChild(cellText(fmtQty(t.qty), "num"));

        // Beneficio
        var profitStr = "—";
        var profitCls = "num pnl";
        if (t.type === "grid_sell" && isNum(t.profit)) {
          profitStr = "+" + fmtPrice(t.profit);
          profitCls += " is-pos";
        } else if (t.type === "stop_loss_exit" && isNum(t.profit)) {
          profitStr = (t.profit < 0 ? "-" : "+") + fmtPrice(Math.abs(t.profit));
          profitCls += t.profit < 0 ? " is-neg" : " is-pos";
        }
        tr.appendChild(cellText(profitStr, profitCls));

        self.dom.tradesBody.appendChild(tr);
      });
    },

    renderPriceChart: function (data) {
      var dates = data.dates || [];
      var trades = data.trades || [];
      var gridLevels = data.grid_levels || [];

      var traces = [
        {
          type: "scatter",
          mode: "lines",
          name: "Precio",
          x: dates,
          y: data.close || [],
          line: { color: C.close, width: 1.5 },
          connectgaps: false,
          hovertemplate: "%{x}<br>Precio: $%{y:,.4~f}<extra>Precio Cierre</extra>"
        }
      ];

      var buyX = [], buyY = [], buyMeta = [];
      var sellX = [], sellY = [], sellMeta = [];
      var stopX = [], stopY = [];

      trades.forEach(function (t) {
        if (t.type === "grid_buy") {
          buyX.push(t.date);
          buyY.push(t.price);
          buyMeta.push([fmtQty(t.qty)]);
        } else if (t.type === "grid_sell") {
          sellX.push(t.date);
          sellY.push(t.price);
          sellMeta.push([fmtPrice(t.profit || 0)]);
        } else if (t.type === "stop_loss_exit") {
          stopX.push(t.date);
          stopY.push(t.price);
        }
      });

      if (buyX.length) {
        traces.push({
          type: "scatter",
          mode: "markers",
          name: "Compra Malla",
          x: buyX,
          y: buyY,
          customdata: buyMeta,
          marker: { color: C.entry, size: 8, symbol: "triangle-up", line: { color: "#0c0a17", width: 1 } },
          hovertemplate: "<b>Compra Malla</b><br>Nivel: $%{y:,.4~f}<br>Cantidad: %{customdata[0]}<extra></extra>"
        });
      }

      if (sellX.length) {
        traces.push({
          type: "scatter",
          mode: "markers",
          name: "Venta con Beneficio",
          x: sellX,
          y: sellY,
          customdata: sellMeta,
          marker: { color: C.gridSell, size: 8, symbol: "triangle-down", line: { color: "#0c0a17", width: 1 } },
          hovertemplate: "<b>Venta con Beneficio</b><br>Nivel: $%{y:,.4~f}<br>Beneficio: +%{customdata[0]}<extra></extra>"
        });
      }

      if (stopX.length) {
        traces.push({
          type: "scatter",
          mode: "markers",
          name: "Stop-Loss",
          x: stopX,
          y: stopY,
          marker: { color: C.exitStop, size: 10, symbol: "x", line: { color: "#0c0a17", width: 1.5 } },
          hovertemplate: "<b>Stop-Loss de Seguridad</b><br>Precio: $%{y:,.4~f}<extra></extra>"
        });
      }

      var layout = baseLayout();
      layout.yaxis.title = { text: "Precio (USDT)", font: { family: SANS, size: 11.5, color: C.faint } };

      // Líneas horizontales para cada nivel de la rejilla
      layout.shapes = gridLevels.map(function (lvl, idx) {
        var isBoundary = (idx === 0 || idx === gridLevels.length - 1);
        return {
          type: "line",
          xref: "paper", x0: 0, x1: 1,
          yref: "y", y0: lvl, y1: lvl,
          line: {
            color: isBoundary ? "rgba(124, 107, 255, 0.6)" : "rgba(124, 107, 255, 0.22)",
            width: isBoundary ? 1.5 : 1,
            dash: isBoundary ? "solid" : "dot"
          },
          layer: "below"
        };
      });

      if (gridLevels.length >= 2) {
        layout.annotations = [
          {
            xref: "paper", x: 1, xanchor: "right",
            yref: "y", y: gridLevels[0], yanchor: "top",
            text: "Límite inf. " + fmtPrice(gridLevels[0]),
            showarrow: false,
            font: { family: MONO, size: 10, color: C.faint }
          },
          {
            xref: "paper", x: 1, xanchor: "right",
            yref: "y", y: gridLevels[gridLevels.length - 1], yanchor: "bottom",
            text: "Límite sup. " + fmtPrice(gridLevels[gridLevels.length - 1]),
            showarrow: false,
            font: { family: MONO, size: 10, color: C.faint }
          }
        ];
      }

      window.Plotly.react(this.dom.chartPrice, traces, layout, PLOT_CONFIG);
    },

    renderEquityChart: function (data) {
      var dates = data.dates || [];
      var equity = data.equity_curve || [];

      var start = null;
      for (var i = 0; i < equity.length; i++) {
        if (isNum(equity[i])) { start = equity[i]; break; }
      }
      var end = null;
      for (var j = equity.length - 1; j >= 0; j--) {
        if (isNum(equity[j])) { end = equity[j]; break; }
      }

      var up = isNum(start) && isNum(end) ? end >= start : true;
      var lineColor = up ? C.entry : C.exitStop;
      var fillColor = up ? "rgba(52, 211, 153, 0.12)" : "rgba(251, 113, 133, 0.12)";

      var traces = [{
        type: "scatter",
        mode: "lines",
        name: "Equity Malla",
        x: dates,
        y: equity,
        line: { color: lineColor, width: 2, shape: "linear" },
        fill: "tozeroy",
        fillcolor: fillColor,
        connectgaps: false,
        hovertemplate: "%{x}<br>Capital: $%{y:,.2f}<extra>Malla</extra>"
      }];

      var layout = baseLayout();
      layout.showlegend = false;
      layout.margin.t = 16;
      layout.yaxis.title = { text: "Capital acumulado (USDT)", font: { family: SANS, size: 11.5, color: C.faint } };
      layout.yaxis.tickprefix = "$";
      layout.yaxis.tickformat = ",.0f";

      var finite = equity.filter(isNum);
      if (finite.length) {
        var lo = Math.min.apply(null, finite);
        var hi = Math.max.apply(null, finite);
        var pad = (hi - lo) * 0.09;
        if (!(pad > 0)) { pad = Math.max(Math.abs(hi) * 0.05, 1); }
        layout.yaxis.range = [lo - pad, hi + pad];
      }

      if (isNum(start) && dates.length) {
        layout.shapes = [{
          type: "line",
          xref: "paper", x0: 0, x1: 1,
          yref: "y", y0: start, y1: start,
          line: { color: "rgba(255,255,255,0.25)", width: 1, dash: "dot" },
          layer: "below"
        }];
        layout.annotations = [{
          xref: "paper", x: 1, xanchor: "right",
          yref: "y", y: start, yanchor: "bottom",
          text: "Capital asignado " + fmtMoney(start),
          showarrow: false,
          font: { family: MONO, size: 10.5, color: C.faint }
        }];
      }

      window.Plotly.react(this.dom.chartEquity, traces, layout, PLOT_CONFIG);
    },

    resize: function () {
      if (this.chartsDrawn && window.Plotly) {
        window.Plotly.Plots.resize(this.dom.chartPrice);
        window.Plotly.Plots.resize(this.dom.chartEquity);
      }
    }
  };

  /* ═══════════════════════════════════════════════════════════════
     SISTEMA DE NAVEGACIÓN ENTRE PESTAÑAS (TABS)
     ═══════════════════════════════════════════════════════════════ */
  var tabBtnBt = $("tab-btn-bt");
  var tabBtnGrid = $("tab-btn-grid");
  var panelBt = $("panel-bt");
  var panelGrid = $("panel-grid");

  function switchTab(activeTabId) {
    var isBt = activeTabId === "tab-btn-bt";

    // Actualizar botones de pestaña
    tabBtnBt.classList.toggle("is-active", isBt);
    tabBtnBt.setAttribute("aria-selected", isBt ? "true" : "false");
    tabBtnBt.setAttribute("tabindex", isBt ? "0" : "-1");

    tabBtnGrid.classList.toggle("is-active", !isBt);
    tabBtnGrid.setAttribute("aria-selected", !isBt ? "true" : "false");
    tabBtnGrid.setAttribute("tabindex", !isBt ? "0" : "-1");

    // Actualizar paneles
    panelBt.hidden = !isBt;
    panelGrid.hidden = isBt;

    // Redimensionar gráficos Plotly en la pestaña recién activada
    window.requestAnimationFrame(function () {
      if (isBt) {
        btTab.resize();
      } else {
        gridTab.resize();
      }
    });
  }

  tabBtnBt.addEventListener("click", function () {
    switchTab("tab-btn-bt");
  });

  tabBtnGrid.addEventListener("click", function () {
    switchTab("tab-btn-grid");
  });

  // Navegación accesible por teclado (ArrowLeft, ArrowRight)
  var tabsList = [tabBtnBt, tabBtnGrid];
  tabsList.forEach(function (btn, idx) {
    btn.addEventListener("keydown", function (ev) {
      var targetIdx = null;
      if (ev.key === "ArrowRight") {
        targetIdx = (idx + 1) % tabsList.length;
      } else if (ev.key === "ArrowLeft") {
        targetIdx = (idx - 1 + tabsList.length) % tabsList.length;
      } else if (ev.key === "Home") {
        targetIdx = 0;
      } else if (ev.key === "End") {
        targetIdx = tabsList.length - 1;
      }

      if (targetIdx !== null) {
        ev.preventDefault();
        tabsList[targetIdx].focus();
        switchTab(tabsList[targetIdx].id);
      }
    });
  });

  /* ═══════════════════════════════════════════════════════════════
     CARGA DE SÍMBOLOS DISPONIBLES
     ═══════════════════════════════════════════════════════════════ */
  function loadSymbols() {
    btTab.dom.runBtn.disabled = true;
    gridTab.dom.runBtn.disabled = true;

    return fetch("/api/symbols")
      .then(function (res) {
        if (!res.ok) { throw new Error("HTTP " + res.status); }
        return res.json();
      })
      .then(function (data) {
        var syms = (data && data.symbols) || [];
        if (!syms.length) { throw new Error("La lista de símbolos está vacía."); }

        // Poblar select de Backtesting
        btTab.dom.symbol.innerHTML = "";
        gridTab.dom.symbol.innerHTML = "";

        syms.forEach(function (s) {
          var opt1 = document.createElement("option");
          opt1.value = s;
          opt1.textContent = s;
          btTab.dom.symbol.appendChild(opt1);

          var opt2 = document.createElement("option");
          opt2.value = s;
          opt2.textContent = s;
          gridTab.dom.symbol.appendChild(opt2);
        });

        btTab.dom.runBtn.disabled = false;
        gridTab.dom.runBtn.disabled = false;
      })
      .catch(function (err) {
        var fallback = '<option value="">No disponible</option>';
        btTab.dom.symbol.innerHTML = fallback;
        btTab.dom.symbol.disabled = true;
        gridTab.dom.symbol.innerHTML = fallback;
        gridTab.dom.symbol.disabled = true;

        var msg = "No se pudo cargar la lista de símbolos (" + err.message + "). ¿Está encendido el servidor FastAPI?";
        btTab.showError(msg);
        gridTab.showError(msg);
      });
  }

  /* ═══════════════════════════════════════════════════════════════
     EVENT LISTENERS Y ARRANQUE
     ═══════════════════════════════════════════════════════════════ */
  // Botones de Ejecución
  btTab.dom.runBtn.addEventListener("click", function () { btTab.run(); });
  btTab.dom.errorDismiss.addEventListener("click", function () { btTab.hideError(); });
  btTab.dom.symbol.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") { ev.preventDefault(); btTab.run(); }
  });

  gridTab.dom.runBtn.addEventListener("click", function () { gridTab.run(); });
  gridTab.dom.errorDismiss.addEventListener("click", function () { gridTab.hideError(); });
  gridTab.dom.symbol.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") { ev.preventDefault(); gridTab.run(); }
  });
  gridTab.dom.numGrids.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") { ev.preventDefault(); gridTab.run(); }
  });
  gridTab.dom.lowerPrice.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") { ev.preventDefault(); gridTab.run(); }
  });
  gridTab.dom.upperPrice.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") { ev.preventDefault(); gridTab.run(); }
  });

  // Redimensionamiento de ventana
  window.addEventListener("resize", function () {
    if (!panelBt.hidden) {
      btTab.resize();
    }
    if (!panelGrid.hidden) {
      gridTab.resize();
    }
  });

  // Carga inicial
  loadSymbols();
})();
