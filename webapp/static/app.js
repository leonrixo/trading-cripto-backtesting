/* =============================================================
   Backtester · lógica del frontend
   Sin build step: JS plano, un IIFE, sin dependencias salvo Plotly (CDN).
   ============================================================= */
(function () {
  "use strict";

  /* ── Paleta compartida con style.css (las gráficas no leen CSS) ──
     OJO: `faint` es el espejo de --text-faint en style.css y se usa en los ticks de
     los ejes, que son texto chico. Si cambia uno tiene que cambiar el otro; el valor
     cumple 4.5:1 de WCAG AA sobre el fondo de los paneles (5.07:1). */
  var C = {
    text:      "#e9edf6",
    dim:       "#98a1b6",
    faint:     "#7c879d",
    grid:      "rgba(255,255,255,.055)",
    axis:      "rgba(255,255,255,.12)",
    surface:   "#161a27",
    close:     "#c9d4e8",
    fastMa:    "#fbbf24",
    slowMa:    "#7c6bff",
    entry:     "#34d399",
    exitSig:   "#60a5fa",
    exitStop:  "#fb7185",
    exitEnd:   "#94a3b8"
  };

  var SANS = 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  var MONO = 'JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';

  var PLOT_CONFIG = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["select2d", "lasso2d", "toggleSpikelines"],
    toImageButtonOptions: { format: "png", scale: 2 }
  };

  /* ── Referencias al DOM ─────────────────────────────────────── */
  var $ = function (id) { return document.getElementById(id); };

  var elSymbol       = $("symbol");
  var elRun          = $("run");
  var elError        = $("error");
  var elErrorMessage = $("error-message");
  var elErrorDismiss = $("error-dismiss");
  var elEmpty        = $("empty");
  var elLoading      = $("loading");
  var elLoadingSym   = $("loading-symbol");
  var elLoadingTimer = $("loading-timer");
  var elResults      = $("results");
  var elResultsSym   = $("results-symbol");
  var elResultsMeta  = $("results-meta");
  var elTradesBody   = $("trades-body");
  var elTradesCount  = $("trades-count");
  var elChartPrice   = $("chart-price");
  var elChartEquity  = $("chart-equity");
  var elParamFast    = $("param-fast");
  var elParamSlow    = $("param-slow");
  var elParamStop    = $("param-stop");
  var elParamCapital = $("param-capital");

  var METRIC_NODES = {
    total_return: $("m-total-return"),
    win_rate:     $("m-win-rate"),
    max_drawdown: $("m-max-drawdown"),
    sharpe_ratio: $("m-sharpe"),
    num_trades:   $("m-num-trades")
  };

  var timerId = null;
  var chartsDrawn = false;
  var running = false;

  /* ── Formateo ───────────────────────────────────────────────── */
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

  /* Los pares van de ~$0.05 (DOGE) a ~$100,000 (BTC): decimales adaptativos. */
  function priceDecimals(v) {
    var abs = Math.abs(v);
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

  /* Colorea el número Y el borde de la tarjeta. */
  function signClass(v) {
    if (!isNum(v) || v === 0) { return ""; }
    return v > 0 ? "is-pos" : "is-neg";
  }

  /* Colorea solo el número, sin teñir la tarjeta. */
  function quietSignClass(v) {
    if (!isNum(v) || v === 0) { return ""; }
    return v > 0 ? "is-quiet-pos" : "is-quiet-neg";
  }

  /* ── Manejo de estados de la pantalla ───────────────────────── */
  function showError(message) {
    elErrorMessage.textContent = message;
    elError.hidden = false;
  }

  function hideError() {
    elError.hidden = true;
    elErrorMessage.textContent = "";
  }

  /* Requisito: un error nunca puede convivir con resultados viejos. */
  function clearResults() {
    elResults.hidden = true;
    if (chartsDrawn && window.Plotly) {
      window.Plotly.purge(elChartPrice);
      window.Plotly.purge(elChartEquity);
      chartsDrawn = false;
    }
    elTradesBody.innerHTML = "";
    Object.keys(METRIC_NODES).forEach(function (key) {
      var node = METRIC_NODES[key];
      node.textContent = "—";
      node.className = "metric__value";
    });
    resetParams();
  }

  function resetParams() {
    elParamFast.textContent = "—";
    elParamSlow.textContent = "—";
    elParamStop.textContent = "—";
    elParamCapital.textContent = "—";
  }

  function startTimer() {
    var t0 = Date.now();
    elLoadingTimer.textContent = "0.0s";
    stopTimer();
    timerId = window.setInterval(function () {
      elLoadingTimer.textContent = ((Date.now() - t0) / 1000).toFixed(1) + "s";
    }, 100);
  }

  function stopTimer() {
    if (timerId !== null) {
      window.clearInterval(timerId);
      timerId = null;
    }
  }

  function setBusy(busy, symbol) {
    running = busy;
    elRun.disabled = busy;
    elSymbol.disabled = busy;
    elRun.classList.toggle("is-busy", busy);
    elRun.setAttribute("aria-busy", busy ? "true" : "false");
    elRun.querySelector(".btn__label").textContent = busy ? "Corriendo…" : "Correr backtest";

    if (busy) {
      elLoadingSym.textContent = symbol || "—";
      elLoading.hidden = false;
      elEmpty.hidden = true;
      startTimer();
    } else {
      elLoading.hidden = true;
      stopTimer();
    }
  }

  /* ── Carga de símbolos ──────────────────────────────────────── */
  function loadSymbols() {
    elRun.disabled = true;
    return fetch("/api/symbols")
      .then(function (res) {
        if (!res.ok) { throw new Error("HTTP " + res.status); }
        return res.json();
      })
      .then(function (data) {
        var symbols = (data && data.symbols) || [];
        if (!symbols.length) { throw new Error("la lista de símbolos llegó vacía"); }

        elSymbol.innerHTML = "";
        symbols.forEach(function (sym) {
          var opt = document.createElement("option");
          opt.value = sym;
          opt.textContent = sym;
          elSymbol.appendChild(opt);
        });
        elRun.disabled = false;
      })
      .catch(function (err) {
        elSymbol.innerHTML = "";
        var opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No disponible";
        elSymbol.appendChild(opt);
        elSymbol.disabled = true;
        elRun.disabled = true;
        showError("No se pudo cargar la lista de símbolos (" + err.message +
                  "). ¿Está corriendo el servidor?");
      });
  }

  /* ── Corrida del backtest ───────────────────────────────────── */
  function runBacktest() {
    if (running) { return; }

    var symbol = elSymbol.value;
    if (!symbol) {
      showError("Elige un símbolo antes de correr el backtest.");
      return;
    }

    hideError();
    clearResults();
    setBusy(true, symbol);

    fetch("/api/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: symbol })
    })
      .then(function (res) {
        // El cuerpo puede no ser JSON (p. ej. un 500 en HTML): no debe romper el flujo.
        return res.json().then(
          function (body) { return { ok: res.ok, status: res.status, body: body }; },
          function () { return { ok: res.ok, status: res.status, body: null }; }
        );
      })
      .then(function (result) {
        if (!result.ok) {
          var detail = result.body && result.body.detail;
          throw explained(detail || ("El servidor respondió " + result.status + "."));
        }
        if (!result.body) {
          throw explained("La respuesta del servidor no es JSON válido.");
        }
        setBusy(false);
        render(result.body);
      })
      .catch(function (err) {
        setBusy(false);
        clearResults();
        elEmpty.hidden = true;
        // Solo los errores que armamos nosotros traen un mensaje mostrable; un
        // rechazo crudo de fetch diría "Failed to fetch", que no le dice nada a nadie.
        showError(err && err.explained
          ? err.message
          : "No se pudo contactar al servidor. Revisa que siga corriendo en " +
            "http://127.0.0.1:8000 y vuelve a intentar.");
      });
  }

  /* Marca un error como "tiene un mensaje pensado para el usuario". */
  function explained(message) {
    var err = new Error(message);
    err.explained = true;
    return err;
  }

  /* ── Render ─────────────────────────────────────────────────── */
  function render(data) {
    // La app es local pero Plotly viene del CDN: sin internet no carga.
    if (!window.Plotly) {
      throw explained("No se pudo cargar Plotly.js desde el CDN. Revisa tu conexión " +
                      "a internet y recarga la página.");
    }

    hideError();
    elEmpty.hidden = true;

    renderParams(data.params || {});
    renderHeader(data);
    renderMetrics(data.metrics || {});
    renderTrades(data.trades || []);

    elResults.hidden = false;

    // Plotly necesita que el contenedor sea visible para medir su ancho.
    renderPriceChart(data);
    renderEquityChart(data);
    chartsDrawn = true;
  }

  /* Los chips del header vienen hardcodeados en el HTML hasta la primera corrida
     exitosa; a partir de ahí reflejan lo que el backend realmente usó, no un
     literal que podría desincronizarse de src/main.py. */
  function renderParams(p) {
    elParamFast.textContent    = isNum(p.fast_window)    ? String(p.fast_window) : "—";
    elParamSlow.textContent    = isNum(p.slow_window)    ? String(p.slow_window) : "—";
    elParamStop.textContent    = isNum(p.stop_loss_pct)  ? fmtPct(p.stop_loss_pct, 0) : "—";
    elParamCapital.textContent = isNum(p.initial_capital) ? fmtMoney(p.initial_capital) : "—";
  }

  function renderHeader(data) {
    var dates = data.dates || [];
    elResultsSym.textContent = data.symbol || "—";

    var parts = [];
    if (dates.length) {
      parts.push(dates[0] + " → " + dates[dates.length - 1]);
      parts.push(dates.length + " velas diarias");
    }
    var equity = data.equity_curve || [];
    var last = equity.length ? equity[equity.length - 1] : null;
    if (isNum(last)) { parts.push("equity final " + fmtMoney(last)); }

    elResultsMeta.textContent = parts.join("  ·  ") || "—";
  }

  function renderMetrics(m) {
    // Solo el retorno total pinta el borde de color de su tarjeta: es el resultado
    // de la corrida. El drawdown siempre es negativo, así que teñir su tarjeta de
    // rojo en cada corrida diluiría la señal; se colorea solo el número.
    setMetric(METRIC_NODES.total_return, fmtSignedPct(m.total_return, 1), signClass(m.total_return));
    setMetric(METRIC_NODES.win_rate,     fmtPct(m.win_rate, 1), "");
    setMetric(METRIC_NODES.max_drawdown, fmtPct(m.max_drawdown, 1), "is-risk");
    setMetric(METRIC_NODES.sharpe_ratio, fmtNum(m.sharpe_ratio, 2), quietSignClass(m.sharpe_ratio));
    setMetric(METRIC_NODES.num_trades,   isNum(m.num_trades) ? String(Math.round(m.num_trades)) : "—", "");
  }

  function setMetric(node, text, cls) {
    node.textContent = text;
    node.className = "metric__value" + (cls ? " " + cls : "");
  }

  var REASON_LABEL = {
    signal: "Señal",
    stop_loss: "Stop-loss",
    end_of_data: "Fin de datos"
  };

  var REASON_CLASS = {
    signal: "tag--signal",
    stop_loss: "tag--stop",
    end_of_data: "tag--end"
  };

  function renderTrades(trades) {
    elTradesBody.innerHTML = "";
    elTradesCount.textContent = trades.length
      ? trades.length + (trades.length === 1 ? " operación" : " operaciones")
      : "Sin operaciones";

    if (!trades.length) {
      var emptyRow = document.createElement("tr");
      emptyRow.className = "empty-row";
      var cell = document.createElement("td");
      cell.colSpan = 6;
      cell.textContent = "La estrategia no abrió ninguna posición en este periodo.";
      emptyRow.appendChild(cell);
      elTradesBody.appendChild(emptyRow);
      return;
    }

    trades.forEach(function (t) {
      var tr = document.createElement("tr");

      tr.appendChild(cellText(t.entry_date, "date"));
      tr.appendChild(cellText(t.exit_date, "date"));
      tr.appendChild(cellText(fmtPrice(t.entry_price), "num"));
      tr.appendChild(cellText(fmtPrice(t.exit_price), "num"));
      tr.appendChild(cellText(fmtSignedPct(t.pnl_pct, 2), "num pnl " + signClass(t.pnl_pct)));

      var tdReason = document.createElement("td");
      var tag = document.createElement("span");
      tag.className = "tag " + (REASON_CLASS[t.exit_reason] || "tag--end");
      tag.textContent = REASON_LABEL[t.exit_reason] || t.exit_reason || "—";
      tdReason.appendChild(tag);
      tr.appendChild(tdReason);

      elTradesBody.appendChild(tr);
    });
  }

  function cellText(text, cls) {
    var td = document.createElement("td");
    td.textContent = text == null ? "—" : text;
    if (cls) { td.className = cls.trim(); }
    return td;
  }

  /* ── Gráficas ───────────────────────────────────────────────── */
  function baseLayout() {
    return {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: SANS, size: 12, color: C.dim },
      margin: { l: 66, r: 22, t: 10, b: 44 },
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
        spikecolor: "rgba(255,255,255,.28)"
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

  function markerTrace(name, x, y, color, symbol, customdata, hovertemplate) {
    return {
      type: "scatter",
      mode: "markers",
      name: name,
      x: x,
      y: y,
      customdata: customdata,
      marker: {
        color: color,
        size: 10,
        symbol: symbol,
        line: { color: "rgba(10,12,17,.9)", width: 1.2 }
      },
      hovertemplate: hovertemplate
    };
  }

  function renderPriceChart(data) {
    var dates = data.dates || [];
    var trades = data.trades || [];
    var params = data.params || {};
    var fastName = "MA " + (isNum(params.fast_window) ? params.fast_window : "?");
    var slowName = "MA " + (isNum(params.slow_window) ? params.slow_window : "?");

    var traces = [
      {
        type: "scatter",
        mode: "lines",
        name: "Cierre",
        x: dates,
        y: data.close || [],
        line: { color: C.close, width: 1.4 },
        connectgaps: false,
        hovertemplate: "%{y:,.6~f}<extra>Cierre</extra>"
      },
      {
        type: "scatter",
        mode: "lines",
        name: fastName,
        x: dates,
        y: data.fast_ma || [],
        line: { color: C.fastMa, width: 1.8 },
        connectgaps: false,
        hovertemplate: "%{y:,.6~f}<extra>" + fastName + "</extra>"
      },
      {
        type: "scatter",
        mode: "lines",
        name: slowName,
        x: dates,
        y: data.slow_ma || [],
        line: { color: C.slowMa, width: 1.8 },
        connectgaps: false,
        hovertemplate: "%{y:,.6~f}<extra>" + slowName + "</extra>"
      }
    ];

    // Entradas y salidas se derivan de `trades`, nunca de la columna `signal`.
    var entryX = [], entryY = [], entryMeta = [];
    var buckets = {
      signal:      { x: [], y: [], meta: [] },
      stop_loss:   { x: [], y: [], meta: [] },
      end_of_data: { x: [], y: [], meta: [] }
    };

    trades.forEach(function (t) {
      entryX.push(t.entry_date);
      entryY.push(t.entry_price);
      entryMeta.push([fmtPrice(t.entry_price)]);

      var bucket = buckets[t.exit_reason] || buckets.end_of_data;
      bucket.x.push(t.exit_date);
      bucket.y.push(t.exit_price);
      bucket.meta.push([fmtPrice(t.exit_price), fmtSignedPct(t.pnl_pct, 2)]);
    });

    if (entryX.length) {
      traces.push(markerTrace(
        "Entrada", entryX, entryY, C.entry, "triangle-up", entryMeta,
        "%{customdata[0]}<extra>Entrada</extra>"
      ));
    }

    var exitSpecs = [
      { key: "signal",      label: "Salida · señal",        color: C.exitSig,  symbol: "triangle-down" },
      { key: "stop_loss",   label: "Salida · stop-loss",    color: C.exitStop, symbol: "x" },
      { key: "end_of_data", label: "Salida · fin de datos", color: C.exitEnd,  symbol: "circle-open" }
    ];

    exitSpecs.forEach(function (spec) {
      var b = buckets[spec.key];
      if (!b.x.length) { return; }
      traces.push(markerTrace(
        spec.label, b.x, b.y, spec.color, spec.symbol, b.meta,
        "%{customdata[0]}  (%{customdata[1]})<extra>" + spec.label + "</extra>"
      ));
    });

    var layout = baseLayout();
    layout.yaxis.title = { text: "Precio (USDT)", font: { family: SANS, size: 11.5, color: C.faint } };

    window.Plotly.react(elChartPrice, traces, layout, PLOT_CONFIG);
  }

  function renderEquityChart(data) {
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
    var line = up ? C.entry : C.exitStop;
    var fill = up ? "rgba(52,211,153,.13)" : "rgba(251,113,133,.13)";

    var traces = [{
      type: "scatter",
      mode: "lines",
      name: "Equity",
      x: dates,
      y: equity,
      line: { color: line, width: 2, shape: "linear" },
      fill: "tozeroy",
      fillcolor: fill,
      connectgaps: false,
      hovertemplate: "$%{y:,.2f}<extra>Equity</extra>"
    }];

    var layout = baseLayout();
    layout.showlegend = false;
    layout.margin.t = 16;
    layout.yaxis.title = { text: "Valor de la cuenta", font: { family: SANS, size: 11.5, color: C.faint } };
    layout.yaxis.tickprefix = "$";
    layout.yaxis.tickformat = ",.0f";

    // `fill: tozeroy` haría que Plotly estirara el eje hasta 0 y aplanara la curva:
    // fijamos el rango a los datos (con margen) y dejamos que el relleno se recorte.
    var finite = equity.filter(isNum);
    if (finite.length) {
      var lo = Math.min.apply(null, finite);
      var hi = Math.max.apply(null, finite);
      var pad = (hi - lo) * 0.09;
      if (!(pad > 0)) { pad = Math.max(Math.abs(hi) * 0.05, 1); }
      layout.yaxis.range = [lo - pad, hi + pad];
    }

    if (isNum(start) && dates.length) {
      // Línea de referencia: el capital inicial, para leer ganancia/pérdida de un vistazo.
      layout.shapes = [{
        type: "line",
        xref: "paper", x0: 0, x1: 1,
        yref: "y", y0: start, y1: start,
        line: { color: "rgba(255,255,255,.28)", width: 1, dash: "dot" },
        layer: "below"
      }];
      layout.annotations = [{
        xref: "paper", x: 1, xanchor: "right",
        yref: "y", y: start, yanchor: "bottom",
        text: "capital inicial " + fmtMoney(start),
        showarrow: false,
        font: { family: MONO, size: 10.5, color: C.faint }
      }];
    }

    window.Plotly.react(elChartEquity, traces, layout, PLOT_CONFIG);
  }

  /* ── Arranque ───────────────────────────────────────────────── */
  elRun.addEventListener("click", runBacktest);
  elErrorDismiss.addEventListener("click", hideError);

  elSymbol.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      runBacktest();
    }
  });

  document.addEventListener("keydown", function (ev) {
    if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") {
      ev.preventDefault();
      runBacktest();
    }
  });

  loadSymbols();
})();
