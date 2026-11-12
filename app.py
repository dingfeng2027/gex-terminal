<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CAPITAL QUANT v2 | Institutional Market & Options Terminal</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-deep: #020817;
      --bg-navy: #051332;
      --bg-panel: #071940;
      --bg-panel-alt: #091f4d;
      --border-blue: #18449c;
      --border-glow: #2563eb;
      --accent-blue: #1d63ff;
      --accent-cyan: #38bdf8;
      --accent-gold: #facc15;
      --gain-green: #22c55e;
      --loss-red: #ef4444;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 50% 0%, #0a2357 0%, #030b1e 65%, #020612 100%);
      color: #f8fafc;
      min-height: 100vh;
      overflow-x: hidden;
    }

    .font-mono-num {
      font-family: 'JetBrains Mono', monospace;
      font-variant-numeric: tabular-nums;
    }

    /* Terminal Outer Frame & Panels */
    .terminal-shell {
      background: linear-gradient(180deg, rgba(6, 20, 52, 0.96) 0%, rgba(3, 11, 30, 0.98) 100%);
      border: 1px solid #1e4bb8;
      box-shadow: 0 0 35px rgba(29, 99, 255, 0.22), inset 0 1px 0 rgba(147, 197, 253, 0.2);
    }

    .terminal-card {
      background: linear-gradient(180deg, rgba(8, 26, 66, 0.88) 0%, rgba(5, 16, 44, 0.94) 100%);
      border: 1px solid #1a4396;
      box-shadow: inset 0 1px 0 rgba(96, 165, 250, 0.14), 0 4px 20px rgba(0, 0, 0, 0.35);
    }

    .terminal-header-bar {
      background: linear-gradient(90deg, #04102b 0%, #0b2459 50%, #04102b 100%);
      border-bottom: 1px solid #1e4bb8;
    }

    /* Royal Blue Glossy Buttons */
    .btn-royal {
      background: linear-gradient(180deg, #2b75ff 0%, #1450db 100%);
      border: 1px solid #60a5fa;
      box-shadow: 0 2px 10px rgba(29, 99, 255, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.28);
      transition: all 0.15s ease;
    }
    .btn-royal:hover {
      background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 14px rgba(59, 130, 246, 0.6);
    }
    .btn-royal:active {
      transform: translateY(0);
    }

    .btn-amber-glow {
      background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);
      border: 1px solid #fde68a;
      color: #090d16;
      box-shadow: 0 2px 12px rgba(245, 158, 11, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.45);
      transition: all 0.15s ease;
    }
    .btn-amber-glow:hover {
      background: linear-gradient(180deg, #fbbf24 0%, #b45309 100%);
      color: #ffffff;
      transform: translateY(-1px);
    }

    /* Custom Scrollbars */
    ::-webkit-scrollbar {
      width: 7px;
      height: 7px;
    }
    ::-webkit-scrollbar-track {
      background: #040d24;
    }
    ::-webkit-scrollbar-thumb {
      background: #1e4bb8;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #3b82f6;
    }

    /* Grid Table Borders */
    .quant-table {
      border-collapse: collapse;
      width: 100%;
    }
    .quant-table th {
      background: linear-gradient(180deg, #0d2b6b 0%, #081c4a 100%);
      border: 1px solid #1a418f;
      color: #dbeafe;
      font-weight: 700;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      font-size: 0.72rem;
      padding: 9px 8px;
      white-space: nowrap;
    }
    .quant-table td {
      border: 1px solid rgba(29, 78, 173, 0.55);
      padding: 7px 8px;
      white-space: nowrap;
      font-size: 0.84rem;
    }
    .quant-table tbody tr {
      background-color: rgba(6, 19, 50, 0.72);
      transition: background-color 0.14s ease;
    }
    .quant-table tbody tr:nth-child(even) {
      background-color: rgba(9, 26, 66, 0.75);
    }
    .quant-table tbody tr:hover {
      background-color: rgba(29, 99, 255, 0.24);
      cursor: pointer;
    }

    /* Options Chain ITM Highlighting */
    .itm-call {
      background: rgba(16, 185, 129, 0.11) !important;
    }
    .itm-put {
      background: rgba(239, 68, 68, 0.11) !important;
    }

    @keyframes pulse-live {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.45; transform: scale(0.88); }
    }
    .live-dot {
      animation: pulse-live 1.8s infinite ease-in-out;
    }

    @keyframes spin-once {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    .spin-refresh {
      animation: spin-once 0.55s ease-in-out;
    }
  </style>
</head>
<body class="p-2 sm:p-4 md:p-5">

  <!-- Toast / Status Banner (Replaces alert) -->
  <div id="toast-banner" class="fixed bottom-5 right-5 z-50 hidden items-center gap-3 px-4 py-3 rounded-xl bg-[#0b2459] border border-blue-400 text-white shadow-2xl text-sm font-medium transition-all">
    <span id="toast-icon" class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
    <span id="toast-message">Action completed</span>
  </div>

  <!-- Main Terminal Container -->
  <div class="max-w-[1440px] mx-auto rounded-2xl terminal-shell overflow-hidden">

    <!-- ==================== GLOBAL TOP NAVIGATION BAR ==================== -->
    <header class="terminal-header-bar px-3 sm:px-5 py-2.5 flex flex-wrap items-center justify-between gap-3">
      <!-- Brand Logo & Title -->
      <div class="flex items-center gap-2.5 cursor-pointer" onclick="switchPage('market')">
        <div class="w-9 h-9 rounded-lg bg-[#091e4a] border border-blue-500/50 flex items-center justify-center shadow-inner">
          <!-- Gold Candlestick & Trend Icon -->
          <svg class="w-6 h-6" viewBox="0 0 28 28" fill="none">
            <rect x="4" y="13" width="3.5" height="9" rx="0.8" fill="#facc15"/>
            <line x1="5.75" y1="10" x2="5.75" y2="24" stroke="#facc15" stroke-width="1.6"/>
            <rect x="10.5" y="9" width="3.5" height="11" rx="0.8" fill="#fbbf24"/>
            <line x1="12.25" y1="6" x2="12.25" y2="22" stroke="#fbbf24" stroke-width="1.6"/>
            <rect x="17" y="5" width="3.5" height="13" rx="0.8" fill="#fde047"/>
            <line x1="18.75" y1="2.5" x2="18.75" y2="20" stroke="#fde047" stroke-width="1.6"/>
            <path d="M3 16 L11 10 L17 12 L24 4" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M20 4 H24 V8" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <span class="text-white font-extrabold tracking-tight text-lg sm:text-xl">CAPITAL QUANT <span class="text-blue-300 font-bold">v2</span></span>
      </div>

      <!-- Center Navigation Tabs -->
      <nav class="flex flex-wrap items-center gap-1 sm:gap-1.5 text-xs sm:text-sm font-semibold">
        <button id="nav-market" onclick="switchPage('market')" class="nav-tab px-3.5 py-1.5 rounded-lg transition-all btn-royal text-white">
          Market Watch
        </button>
        <button onclick="showToast('Portfolio module synced with live watchlist positions.')" class="px-3 py-1.5 rounded-lg text-blue-200/80 hover:text-white hover:bg-blue-900/40 transition">
          Portfolio
        </button>
        <button id="nav-analysis" onclick="switchPage('analysis')" class="nav-tab px-3.5 py-1.5 rounded-lg transition-all text-blue-200/90 hover:text-white hover:bg-blue-900/40">
          Analysis
        </button>
        <button id="nav-options" onclick="switchPage('options')" class="nav-tab px-3.5 py-1.5 rounded-lg transition-all text-blue-200/90 hover:text-white hover:bg-blue-900/40 flex items-center gap-1.5">
          <span>Options Data</span>
          <span class="px-1.5 py-0.2 text-[10px] rounded bg-amber-400/20 text-amber-300 border border-amber-400/40 font-bold">P/C</span>
        </button>
        <button onclick="switchPage('analysis')" class="hidden md:inline-block px-3 py-1.5 rounded-lg text-blue-200/80 hover:text-white hover:bg-blue-900/40 transition">
          Charts
        </button>
        <button onclick="exportCurrentCSV()" class="hidden lg:inline-block px-3 py-1.5 rounded-lg text-blue-200/80 hover:text-white hover:bg-blue-900/40 transition">
          CSV Import & Data
        </button>
        <button onclick="showToast('Terminal Feed: Institutional Real-Time Stream (Low Latency)')" class="hidden xl:inline-block px-3 py-1.5 rounded-lg text-blue-200/80 hover:text-white hover:bg-blue-900/40 transition">
          Settings
        </button>
      </nav>

      <!-- Right Live Status & Clock -->
      <div class="flex items-center gap-2.5 text-xs font-medium text-blue-100">
        <div class="flex items-center gap-1.5">
          <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399] live-dot"></span>
          <span class="text-emerald-400 font-bold">Live</span>
        </div>
        <span class="text-blue-700">|</span>
        <span id="live-clock" class="font-mono-num text-blue-100/90">Nov 12, 2026 00:32:00</span>
        <span class="text-blue-700 hidden sm:inline">|</span>
        <button onclick="showToast('CAPITAL QUANT v2 workspace snapshot deployed & saved.')" class="hidden sm:inline-block text-blue-200 hover:text-white transition font-semibold">
          Deploy
        </button>
      </div>
    </header>

    <!-- ===================================================================== -->
    <!-- PAGE 1: MARKET WATCH (Matches Screenshot 1)                           -->
    <!-- ===================================================================== -->
    <section id="page-market" class="p-3 sm:p-5 space-y-4">
      <!-- Sub-Header Controls -->
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-[#0a2254] border border-blue-500/50 flex items-center justify-center text-blue-300">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <path d="M8 21h8M12 17v4M6 12l4-4 3 3 5-5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div>
            <h1 class="text-2xl sm:text-[26px] font-extrabold tracking-tight text-white leading-none">Market Watch</h1>
            <p class="text-xs text-blue-300/75 mt-1">Click any company row to open Stock Analysis &amp; Put/Call Options Chain</p>
          </div>
        </div>

        <!-- Search Input & Action Buttons -->
        <div class="flex flex-wrap items-center gap-2.5">
          <div class="relative flex-1 sm:w-72">
            <svg class="w-4 h-4 text-blue-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35" stroke-linecap="round"/>
            </svg>
            <input
              id="ticker-input"
              type="text"
              placeholder="Add Ticker (e.g. NFLX, PLTR, ARM)"
              onkeydown="if(event.key==='Enter') handleAddTicker()"
              class="w-full pl-10 pr-3 py-2 rounded-lg bg-[#051436] border border-blue-500/60 text-sm text-white placeholder-blue-300/50 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/30"
            />
          </div>
          <button onclick="handleAddTicker()" class="btn-royal px-4 py-2 rounded-lg text-xs sm:text-sm font-bold tracking-wide text-white uppercase">
            ADD TICKER
          </button>
          <button onclick="handleUpdateAllSymbols()" class="btn-royal px-4 py-2 rounded-lg text-xs sm:text-sm font-bold tracking-wide text-white uppercase flex items-center gap-2">
            <svg id="refresh-all-icon" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.3" viewBox="0 0 24 24">
              <path d="M21 12a9 9 0 1 1-2.64-6.36L21 8M21 3v5h-5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>UPDATE ALL SYMBOLS</span>
          </button>
        </div>
      </div>

      <!-- Main Market Watch Table Container -->
      <div class="terminal-card rounded-xl overflow-hidden">
        <div class="overflow-x-auto">
          <table class="quant-table">
            <thead>
              <tr>
                <th class="text-left pl-4">COMPANY<br>CODE</th>
                <th class="text-right">TODAY PRICE</th>
                <th class="text-right">YESTERDAY<br>PRICE</th>
                <th class="text-right">CHANGE</th>
                <th class="text-right">% CHANGE</th>
                <th class="text-right">MA20</th>
                <th class="text-right">MA50</th>
                <th class="text-right">MA200</th>
                <th class="text-right">PE RATE</th>
                <th class="text-right">YEARLY<br>HIGH</th>
                <th class="text-right">YEARLY<br>LOW</th>
                <th class="text-center">RSI (14)</th>
                <th class="text-center w-10"></th>
              </tr>
            </thead>
            <tbody id="market-watch-tbody">
              <!-- Dynamically rendered rows -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- Page 1 Bottom Footer Bar -->
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
        <div class="flex flex-wrap items-center gap-2.5">
          <button onclick="openSelectedAnalysis()" class="btn-royal px-5 py-2.5 rounded-xl text-xs sm:text-sm font-extrabold tracking-wide text-white uppercase flex items-center justify-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path d="M3 21h18M4 18h16M6 18V9m4 9V9m4 9V9m4 9V9M3 9l9-6 9 6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>OPEN COMPANY ANALYSIS</span>
            <span class="text-base leading-none">&rsaquo;</span>
          </button>

          <button onclick="openSelectedOptions()" class="px-4 py-2.5 rounded-xl bg-[#0a2254] hover:bg-[#113173] border border-blue-400/50 text-xs sm:text-sm font-bold text-cyan-300 uppercase flex items-center justify-center gap-2 transition">
            <span>PUT &amp; CALL OPTIONS CHAIN</span>
            <span>&rsaquo;</span>
          </button>
        </div>

        <!-- Gainers / Losers / Total Summary Pill -->
        <div class="terminal-card px-4 py-2 rounded-xl flex items-center justify-center sm:justify-end gap-4 text-xs sm:text-sm font-bold">
          <div class="flex items-center gap-1.5 text-emerald-400">
            <span>&#9650;</span>
            <span id="gainers-count">11 Gainers</span>
          </div>
          <span class="text-blue-800">|</span>
          <div class="flex items-center gap-1.5 text-rose-400">
            <span class="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
            <span id="losers-count">1 Loser</span>
          </div>
          <span class="text-blue-800">|</span>
          <div id="total-count" class="text-white">Total: 12</div>
        </div>
      </div>
    </section>

    <!-- ===================================================================== -->
    <!-- PAGE 2: STOCK ANALYSIS (Matches Screenshot 2 + Link to Page 3)        -->
    <!-- ===================================================================== -->
    <section id="page-analysis" class="hidden p-3 sm:p-5 space-y-4">
      <!-- Sub-Header Bar -->
      <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-3">
          <button onclick="switchPage('market')" title="Back to Market Watch" class="px-3 py-2 rounded-lg bg-[#081d4a] hover:bg-[#102d6b] border border-blue-500/50 text-blue-200 text-xs font-bold flex items-center gap-1.5 transition">
            <span>&larr;</span>
            <span>Market Watch</span>
          </button>

          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-xl bg-[#0a2254] border border-blue-500/50 flex items-center justify-center text-blue-300">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4M6 12l4-4 3 3 5-5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <h1 class="text-xl sm:text-2xl font-extrabold text-white tracking-tight">Stock Analysis</h1>
          </div>

          <!-- Company Dropdown Selector -->
          <div class="relative min-w-[250px] sm:min-w-[290px]">
            <select
              id="analysis-company-select"
              onchange="handleSelectCompany(this.value)"
              class="w-full appearance-none pl-4 pr-10 py-2 rounded-lg bg-[#06163b] border border-blue-400/70 text-white font-bold text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <!-- Populated dynamically -->
            </select>
            <svg class="w-4 h-4 text-white pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/>
            </svg>
          </div>
        </div>

        <!-- Action Buttons + Page 3 CTA -->
        <div class="flex flex-wrap items-center gap-2">
          <button onclick="runAnalyzeEffect()" class="btn-royal px-4 py-2 rounded-lg text-xs font-bold uppercase text-white">
            ANALYZE
          </button>
          <button onclick="exportCurrentCSV()" class="btn-royal px-4 py-2 rounded-lg text-xs font-bold uppercase text-white">
            EXPORT
          </button>
          <button onclick="runAnalyzeEffect()" class="btn-royal px-4 py-2 rounded-lg text-xs font-bold uppercase text-white flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.3" viewBox="0 0 24 24">
              <path d="M21 12a9 9 0 1 1-2.64-6.36L21 8M21 3v5h-5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>REFRESH</span>
          </button>
          <!-- Direct Navigation Button to Page 3 (Put & Call Options Data) -->
          <button onclick="switchPage('options')" class="btn-amber-glow px-4 py-2 rounded-lg text-xs sm:text-sm font-extrabold uppercase flex items-center gap-1.5">
            <span>PUT &amp; CALL OPTIONS DATA</span>
            <span class="text-base leading-none">&rsaquo;</span>
          </button>
        </div>
      </div>

      <!-- Main Grid: Left Chart Panel + Right Price Level Ladder -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- Left Chart Card (8 cols on lg) -->
        <div class="lg:col-span-8 terminal-card rounded-xl p-3 sm:p-4 flex flex-col justify-between">
          <!-- Indicator Sub-Tabs -->
          <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-blue-800/70">
            <div class="flex flex-wrap items-center gap-1.5">
              <button onclick="setChartMode('price')" id="tab-chart-price" class="chart-mode-btn px-3.5 py-1.5 rounded-lg text-xs font-bold btn-royal text-white">
                Price Chart
              </button>
              <button onclick="setChartMode('rsi')" id="tab-chart-rsi" class="chart-mode-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold text-blue-200 hover:bg-blue-900/50 transition">
                RSI
              </button>
              <button onclick="setChartMode('volume')" id="tab-chart-volume" class="chart-mode-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold text-blue-200 hover:bg-blue-900/50 transition">
                Volume
              </button>
              <button onclick="setChartMode('ma')" id="tab-chart-ma" class="chart-mode-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold text-blue-200 hover:bg-blue-900/50 transition">
                Moving Averages
              </button>
              <button onclick="setChartMode('bb')" id="tab-chart-bb" class="chart-mode-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold text-blue-200 hover:bg-blue-900/50 transition">
                Bollinger Bands
              </button>
            </div>

            <!-- Legend -->
            <div id="chart-legend" class="flex items-center gap-3 text-xs font-semibold">
              <span class="flex items-center gap-1 text-yellow-300"><span class="w-3 h-0.5 bg-yellow-300 inline-block"></span>MA20</span>
              <span class="flex items-center gap-1 text-sky-400"><span class="w-3 h-0.5 bg-sky-400 inline-block"></span>MA50</span>
              <span class="flex items-center gap-1 text-fuchsia-400"><span class="w-3 h-0.5 bg-fuchsia-400 inline-block"></span>MA200</span>
            </div>
          </div>

          <!-- Canvas Chart Wrapper -->
          <div id="chart-container" class="relative w-full h-[320px] sm:h-[360px] mt-3">
            <canvas id="stock-chart-canvas" class="w-full h-full rounded-lg"></canvas>
            <!-- Hover Tooltip -->
            <div id="chart-tooltip" class="hidden pointer-events-none absolute top-2 left-14 bg-[#04102b]/95 border border-blue-400/70 rounded-lg px-3 py-1.5 text-xs font-mono-num text-white shadow-lg">
            </div>
          </div>
        </div>

        <!-- Right Panel: PRICE LEVEL Ladder (4 cols on lg) -->
        <div class="lg:col-span-4 terminal-card rounded-xl overflow-hidden flex flex-col">
          <div class="px-4 py-2.5 bg-gradient-to-r from-[#0b2663] to-[#081b47] border-b border-blue-700/80 flex items-center justify-between">
            <h2 class="text-sm sm:text-base font-extrabold tracking-wide text-white uppercase">PRICE LEVEL</h2>
            <span class="text-[11px] font-semibold text-blue-300">Target / Stop Ladder</span>
          </div>
          <div id="price-level-list" class="divide-y divide-blue-900/70 flex-1 flex flex-col justify-between text-xs sm:text-sm font-mono-num">
            <!-- Dynamically populated +30% to -30% -->
          </div>
        </div>
      </div>

      <!-- Bottom Panel: KEY DATA (Matches Screenshot 2) -->
      <div class="terminal-card rounded-xl overflow-hidden">
        <div class="px-4 py-2 bg-gradient-to-r from-[#0d2b6b] via-[#091e4d] to-[#0d2b6b] border-b border-blue-700/80 flex items-center justify-between">
          <h3 class="text-sm font-extrabold uppercase tracking-wider text-white">KEY DATA</h3>
          <span id="key-data-subtitle" class="text-xs text-blue-300 font-medium">Real-Time Fundamental &amp; Technical Snapshot</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-blue-800/80">
          <!-- Column 1 -->
          <div class="p-3.5 sm:p-4 space-y-2.5 text-sm">
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">Current Price</span>
              <div class="font-mono-num font-bold text-right">
                <span id="kd-current-price" class="text-white text-base">177.34</span>
                <span id="kd-price-change" class="ml-1.5 text-xs text-rose-400">-9.30 -4.98%</span>
              </div>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">Day High</span>
              <span id="kd-day-high" class="font-mono-num font-bold text-white">188.72</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">Day Low</span>
              <span id="kd-day-low" class="font-mono-num font-bold text-white">175.40</span>
            </div>
          </div>

          <!-- Column 2 -->
          <div class="p-3.5 sm:p-4 space-y-2.5 text-sm">
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">52 Week High</span>
              <span id="kd-52-high" class="font-mono-num font-bold text-white">195.95</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">52 Week Low</span>
              <span id="kd-52-low" class="font-mono-num font-bold text-white">86.62</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">Market Cap</span>
              <span id="kd-mkt-cap" class="font-mono-num font-bold text-white">4.34T</span>
            </div>
          </div>

          <!-- Column 3 -->
          <div class="p-3.5 sm:p-4 space-y-2.5 text-sm">
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">P/E Ratio</span>
              <span id="kd-pe-ratio" class="font-mono-num font-bold text-white">22.43</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">EPS</span>
              <span id="kd-eps" class="font-mono-num font-bold text-white">7.91</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-blue-200/80 font-medium">RSI (14)</span>
              <span id="kd-rsi-badge" class="font-mono-num font-bold px-3 py-0.5 rounded-md text-xs bg-amber-400 text-slate-950">38.7</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===================================================================== -->
    <!-- PAGE 3: PUT & CALL OPTION DATA (Linked from Page 2 & Top Navbar)      -->
    <!-- ===================================================================== -->
    <section id="page-options" class="hidden p-3 sm:p-5 space-y-4">
      <!-- Sub-Header Bar -->
      <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-3">
          <button onclick="switchPage('analysis')" class="px-3 py-2 rounded-lg bg-[#081d4a] hover:bg-[#102d6b] border border-blue-500/50 text-blue-200 text-xs font-bold flex items-center gap-1.5 transition">
            <span>&larr;</span>
            <span>Back to Stock Analysis</span>
          </button>

          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-xl bg-[#0a2254] border border-amber-400/50 flex items-center justify-center text-amber-300">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M4 17l6-6 4 4 6-8" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="20" cy="7" r="2" fill="currentColor"/>
              </svg>
            </div>
            <div>
              <h1 class="text-xl sm:text-2xl font-extrabold text-white tracking-tight">Put &amp; Call Option Data</h1>
              <p class="text-xs text-blue-300/75">Institutional Straddle Chain, Implied Volatility &amp; Greeks</p>
            </div>
          </div>

          <!-- Synced Company Dropdown -->
          <div class="relative min-w-[240px] sm:min-w-[280px]">
            <select
              id="options-company-select"
              onchange="handleSelectCompany(this.value)"
              class="w-full appearance-none pl-4 pr-10 py-2 rounded-lg bg-[#06163b] border border-blue-400/70 text-white font-bold text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <!-- Populated dynamically -->
            </select>
            <svg class="w-4 h-4 text-white pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/>
            </svg>
          </div>
        </div>

        <!-- Expiration Date Pills & Filter -->
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex items-center bg-[#051436] p-1 rounded-xl border border-blue-700/80 gap-1">
            <button onclick="setOptionExpiry(0)" id="exp-btn-0" class="exp-pill px-2.5 py-1.5 rounded-lg text-xs font-bold btn-royal text-white">Nov 20, 2026 (8D)</button>
            <button onclick="setOptionExpiry(1)" id="exp-btn-1" class="exp-pill px-2.5 py-1.5 rounded-lg text-xs font-semibold text-blue-200 hover:bg-blue-900/40">Dec 18, 2026 (36D)</button>
            <button onclick="setOptionExpiry(2)" id="exp-btn-2" class="exp-pill px-2.5 py-1.5 rounded-lg text-xs font-semibold text-blue-200 hover:bg-blue-900/40">Jan 15, 2027 (64D)</button>
            <button onclick="setOptionExpiry(3)" id="exp-btn-3" class="exp-pill px-2.5 py-1.5 rounded-lg text-xs font-semibold text-blue-200 hover:bg-blue-900/40">Mar 19, 2027 (127D)</button>
          </div>

          <button onclick="toggleStrikeRange()" id="strike-range-btn" class="px-3 py-2 rounded-lg bg-[#081d4a] hover:bg-[#113173] border border-blue-400/50 text-xs font-bold text-cyan-300">
            Range: All Strikes
          </button>
        </div>
      </div>

      <!-- 4 Top Options Analytics Summary Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="terminal-card rounded-xl p-3.5">
          <div class="text-xs font-semibold text-blue-300/80 uppercase">Underlying Spot Price</div>
          <div class="mt-1 flex items-baseline justify-between">
            <span id="opt-spot-price" class="text-2xl font-extrabold font-mono-num text-white">$177.34</span>
            <span id="opt-spot-change" class="text-xs font-mono-num font-bold text-rose-400">-9.30 (-4.98%)</span>
          </div>
          <div class="mt-1.5 text-[11px] text-blue-200/70">ATM Strike Highlighted in Center Spine</div>
        </div>

        <div class="terminal-card rounded-xl p-3.5">
          <div class="text-xs font-semibold text-blue-300/80 uppercase">Implied Volatility (IV30)</div>
          <div class="mt-1 flex items-baseline justify-between">
            <span id="opt-iv-val" class="text-2xl font-extrabold font-mono-num text-amber-300">46.8%</span>
            <span id="opt-iv-rank" class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-400/20 text-amber-300 border border-amber-400/40">IV Rank: 64</span>
          </div>
          <div class="mt-1.5 text-[11px] text-blue-200/70">Historical Vol (HV20): <span id="opt-hv-val" class="font-mono-num text-white">39.2%</span></div>
        </div>

        <div class="terminal-card rounded-xl p-3.5">
          <div class="text-xs font-semibold text-blue-300/80 uppercase">Put / Call Ratio (Vol &amp; OI)</div>
          <div class="mt-1 flex items-baseline justify-between">
            <span id="opt-pcr-val" class="text-2xl font-extrabold font-mono-num text-cyan-300">0.78</span>
            <span id="opt-sentiment-badge" class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/40">Bullish Skew</span>
          </div>
          <div class="mt-1.5 text-[11px] text-blue-200/70">Call Vol: <span id="opt-call-vol" class="font-mono-num text-emerald-400">142.8K</span> | Put Vol: <span id="opt-put-vol" class="font-mono-num text-rose-400">111.4K</span></div>
        </div>

        <div class="terminal-card rounded-xl p-3.5">
          <div class="text-xs font-semibold text-blue-300/80 uppercase">Max Pain &amp; Expected Move</div>
          <div class="mt-1 flex items-baseline justify-between">
            <span id="opt-max-pain" class="text-2xl font-extrabold font-mono-num text-white">$180.00</span>
            <span id="opt-exp-move" class="text-xs font-mono-num font-bold text-purple-300">&plusmn;$11.45 (&plusmn;6.46%)</span>
          </div>
          <div class="mt-1.5 text-[11px] text-blue-200/70">1-StdDev Implied Range by Expiration</div>
        </div>
      </div>

      <!-- T-Shaped Straddle Options Chain Table -->
      <div class="terminal-card rounded-xl overflow-hidden">
        <!-- Side Headers -->
        <div class="grid grid-cols-3 bg-[#071b47] border-b border-blue-700/80 text-xs font-extrabold uppercase tracking-wider">
          <div class="px-4 py-2 text-emerald-400 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>CALLS (Bullish Contracts)</span>
          </div>
          <div class="px-4 py-2 text-center text-amber-300 bg-[#0b2459] border-x border-blue-700/80">
            STRIKE PRICE (Click Any Contract for Greeks &amp; Payoff)
          </div>
          <div class="px-4 py-2 text-right text-rose-400 flex items-center justify-end gap-2">
            <span>PUTS (Bearish / Hedge Contracts)</span>
            <span class="w-2 h-2 rounded-full bg-rose-400"></span>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="quant-table text-xs">
            <thead>
              <tr>
                <!-- CALLS HEADERS -->
                <th class="!bg-emerald-950/60 !text-emerald-200 text-right">OI</th>
                <th class="!bg-emerald-950/60 !text-emerald-200 text-right">VOLUME</th>
                <th class="!bg-emerald-950/60 !text-emerald-200 text-right">IV</th>
                <th class="!bg-emerald-950/60 !text-emerald-200 text-right">DELTA</th>
                <th class="!bg-emerald-950/60 !text-emerald-200 text-right">BID</th>
                <th class="!bg-emerald-950/60 !text-emerald-200 text-right">ASK</th>
                <th class="!bg-emerald-950/60 !text-emerald-200 text-right">LAST</th>
                <th class="!bg-emerald-950/60 !text-emerald-200 text-right">% CHG</th>
                <!-- CENTER STRIKE -->
                <th class="!bg-[#133275] !text-amber-300 text-center font-extrabold px-4">STRIKE</th>
                <!-- PUTS HEADERS -->
                <th class="!bg-rose-950/60 !text-rose-200 text-right">% CHG</th>
                <th class="!bg-rose-950/60 !text-rose-200 text-right">LAST</th>
                <th class="!bg-rose-950/60 !text-rose-200 text-right">BID</th>
                <th class="!bg-rose-950/60 !text-rose-200 text-right">ASK</th>
                <th class="!bg-rose-950/60 !text-rose-200 text-right">DELTA</th>
                <th class="!bg-rose-950/60 !text-rose-200 text-right">IV</th>
                <th class="!bg-rose-950/60 !text-rose-200 text-right">VOLUME</th>
                <th class="!bg-rose-950/60 !text-rose-200 text-right">OI</th>
              </tr>
            </thead>
            <tbody id="options-chain-tbody">
              <!-- Populated dynamically -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

  </div>

  <!-- ==================== OPTION CONTRACT PAYOFF & GREEKS MODAL ==================== -->
  <div id="option-modal" class="fixed inset-0 z-50 hidden items-center justify-center bg-black/75 backdrop-blur-sm p-3 sm:p-5">
    <div class="terminal-shell rounded-2xl max-w-2xl w-full overflow-hidden shadow-2xl">
      <div class="terminal-header-bar px-5 py-3.5 flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span id="modal-contract-badge" class="px-2.5 py-0.5 rounded text-xs font-extrabold uppercase bg-emerald-500 text-slate-950">CALL</span>
          <h3 id="modal-contract-title" class="text-base sm:text-lg font-extrabold text-white">NVDA $180.00 Call — Nov 20, 2026</h3>
        </div>
        <button onclick="closeOptionModal()" class="w-8 h-8 rounded-lg bg-blue-900/60 hover:bg-rose-600 text-white font-bold flex items-center justify-center transition">
          &times;
        </button>
      </div>

      <div class="p-5 space-y-4">
        <!-- Contract Pricing & Greeks Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono-num">
          <div class="terminal-card p-3 rounded-xl">
            <div class="text-blue-300/80 font-sans">Mark / Last Price</div>
            <div id="modal-mark" class="text-lg font-extrabold text-white mt-0.5">$6.45</div>
          </div>
          <div class="terminal-card p-3 rounded-xl">
            <div class="text-blue-300/80 font-sans">Breakeven at Exp</div>
            <div id="modal-breakeven" class="text-lg font-extrabold text-amber-300 mt-0.5">$186.45</div>
          </div>
          <div class="terminal-card p-3 rounded-xl">
            <div class="text-blue-300/80 font-sans">Implied Volatility</div>
            <div id="modal-iv" class="text-lg font-extrabold text-cyan-300 mt-0.5">45.2%</div>
          </div>
          <div class="terminal-card p-3 rounded-xl">
            <div class="text-blue-300/80 font-sans">Prob. of Profit</div>
            <div id="modal-pop" class="text-lg font-extrabold text-emerald-400 mt-0.5">41.8%</div>
          </div>
        </div>

        <!-- Full Greeks Strip -->
        <div class="terminal-card rounded-xl p-3 grid grid-cols-5 gap-2 text-center font-mono-num text-xs">
          <div>
            <div class="text-blue-300/75 font-sans text-[11px]">DELTA (&Delta;)</div>
            <div id="modal-delta" class="font-bold text-white text-sm mt-0.5">0.482</div>
          </div>
          <div>
            <div class="text-blue-300/75 font-sans text-[11px]">GAMMA (&Gamma;)</div>
            <div id="modal-gamma" class="font-bold text-white text-sm mt-0.5">0.031</div>
          </div>
          <div>
            <div class="text-blue-300/75 font-sans text-[11px]">THETA (&Theta;)</div>
            <div id="modal-theta" class="font-bold text-rose-400 text-sm mt-0.5">-0.184</div>
          </div>
          <div>
            <div class="text-blue-300/75 font-sans text-[11px]">VEGA (&nu;)</div>
            <div id="modal-vega" class="font-bold text-cyan-300 text-sm mt-0.5">0.142</div>
          </div>
          <div>
            <div class="text-blue-300/75 font-sans text-[11px]">OPEN INT</div>
            <div id="modal-oi" class="font-bold text-amber-300 text-sm mt-0.5">18,420</div>
          </div>
        </div>

        <!-- Payoff Diagram Canvas -->
        <div class="terminal-card rounded-xl p-3">
          <div class="flex items-center justify-between text-xs mb-2">
            <span class="font-bold text-blue-200 uppercase">Expiration Payoff Profile (1 Contract = 100 Shares)</span>
            <span id="modal-max-loss" class="font-mono-num text-rose-400 font-semibold">Max Loss: -$645.00</span>
          </div>
          <div class="h-44 w-full">
            <canvas id="payoff-canvas" class="w-full h-full"></canvas>
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <button onclick="closeOptionModal()" class="px-4 py-2 rounded-lg bg-blue-950 hover:bg-blue-900 border border-blue-500/50 text-xs font-bold text-white">
            CLOSE INSPECTOR
          </button>
          <button onclick="closeOptionModal(); showToast('Simulated option order ticket staged in Paper Portfolio.');" class="btn-royal px-4 py-2 rounded-lg text-xs font-bold text-white">
            STAGE PAPER ORDER
          </button>
        </div>
      </div>
    </div>
  </div>

  <script>
    // =========================================================================
    // 1. MASTER DATASET (Exact values from Screenshots 1 & 2)
    // =========================================================================
    const stocksData = [
      {
        ticker: 'NVDA',
        name: 'NVIDIA Corporation',
        today: 177.34,
        yesterday: 186.64,
        change: -9.30,
        pctChange: -4.98,
        ma20: 209.10,
        ma50: 219.01,
        ma200: 204.62,
        pe: '22.43',
        eps: '7.91',
        mktCap: '4.34T',
        high52: 195.95,
        low52: 86.62,
        rsi: 38.7,
        ivBase: 46.8,
        color: '#22c55e'
      },
      {
        ticker: 'GOOGL',
        name: 'Alphabet Inc.',
        today: 288.93,
        yesterday: 284.78,
        change: 4.15,
        pctChange: 1.46,
        ma20: 314.25,
        ma50: 331.77,
        ma200: 339.32,
        pe: '15.09',
        eps: '19.15',
        mktCap: '3.56T',
        high52: 303.14,
        low52: 142.66,
        rsi: 55.9,
        ivBase: 28.4,
        color: '#3b82f6'
      },
      {
        ticker: 'TSM',
        name: 'Taiwan Semiconductor Mfg.',
        today: 391.23,
        yesterday: 375.44,
        change: 15.79,
        pctChange: 4.21,
        ma20: 413.78,
        ma50: 431.12,
        ma200: 401.76,
        pe: '25.36',
        eps: '15.43',
        mktCap: '2.03T',
        high52: 475.59,
        low52: 260.50,
        rsi: 62.3,
        ivBase: 34.5,
        color: '#ef4444'
      },
      {
        ticker: 'AMD',
        name: 'Advanced Micro Devices',
        today: 509.52,
        yesterday: 449.04,
        change: 60.48,
        pctChange: 13.47,
        ma20: 523.06,
        ma50: 547.69,
        ma200: 417.23,
        pe: '108.81',
        eps: '4.68',
        mktCap: '824.5B',
        high52: 607.31,
        low52: 128.20,
        rsi: 72.5,
        ivBase: 54.2,
        color: '#f97316'
      },
      {
        ticker: 'MSFT',
        name: 'Microsoft Corporation',
        today: 546.89,
        yesterday: 530.61,
        change: 16.28,
        pctChange: 3.07,
        ma20: 531.69,
        ma50: 517.31,
        ma200: 440.25,
        pe: '28.55',
        eps: '19.16',
        mktCap: '4.07T',
        high52: 567.20,
        low52: 349.70,
        rsi: 64.1,
        ivBase: 24.9,
        color: '#38bdf8'
      },
      {
        ticker: 'META',
        name: 'Meta Platforms Inc.',
        today: 644.30,
        yesterday: 610.15,
        change: 34.15,
        pctChange: 5.60,
        ma20: 657.74,
        ma50: 676.24,
        ma200: 631.87,
        pe: '21.99',
        eps: '29.30',
        mktCap: '1.63T',
        high52: 740.91,
        low52: 476.50,
        rsi: 59.4,
        ivBase: 36.1,
        color: '#60a5fa'
      },
      {
        ticker: 'AMZN',
        name: 'Amazon.com Inc.',
        today: 268.44,
        yesterday: 259.30,
        change: 9.14,
        pctChange: 3.52,
        ma20: 254.72,
        ma50: 253.99,
        ma200: 244.09,
        pe: '21.70',
        eps: '12.37',
        mktCap: '2.81T',
        high52: 287.38,
        low52: 161.67,
        rsi: 57.8,
        ivBase: 31.0,
        color: '#fbbf24'
      },
      {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        today: 351.39,
        yesterday: 342.37,
        change: 9.02,
        pctChange: 2.63,
        ma20: 343.91,
        ma50: 336.65,
        ma200: 299.32,
        pe: '39.13',
        eps: '8.98',
        mktCap: '5.28T',
        high52: 377.41,
        low52: 169.21,
        rsi: 61.6,
        ivBase: 23.8,
        color: '#e2e8f0'
      },
      {
        ticker: 'ASML',
        name: 'ASML Holding N.V.',
        today: 1517.98,
        yesterday: 1424.75,
        change: 93.23,
        pctChange: 6.54,
        ma20: 1587.93,
        ma50: 1673.69,
        ma200: 1600.79,
        pe: '37.34',
        eps: '40.65',
        mktCap: '598.4B',
        high52: 1823.54,
        low52: 946.11,
        rsi: 66.2,
        ivBase: 38.7,
        color: '#38bdf8'
      },
      {
        ticker: 'TSLA',
        name: 'Tesla Inc.',
        today: 381.01,
        yesterday: 358.22,
        change: 22.79,
        pctChange: 6.36,
        ma20: 380.57,
        ma50: 372.78,
        ma200: 383.52,
        pe: '418.73',
        eps: '0.91',
        mktCap: '1.21T',
        high52: 488.54,
        low52: 217.20,
        rsi: 58.5,
        ivBase: 58.9,
        color: '#ef4444'
      },
      {
        ticker: 'VUAG.L',
        name: 'Vanguard S&P 500 UCITS ETF',
        today: 108.54,
        yesterday: 107.66,
        change: 0.88,
        pctChange: 0.88,
        ma20: 111.06,
        ma50: 111.29,
        ma200: 105.44,
        pe: 'None',
        eps: 'N/A',
        mktCap: 'ETF',
        high52: 114.69,
        low52: 92.65,
        rsi: 52.1,
        ivBase: 14.2,
        color: '#f43f5e'
      },
      {
        ticker: 'EQQQ.L',
        name: 'Invesco EQQQ Nasdaq-100 ETF',
        today: 405.70,
        yesterday: 402.15,
        change: 3.55,
        pctChange: 0.88,
        ma20: 416.32,
        ma50: 415.87,
        ma200: 392.14,
        pe: 'None',
        eps: 'N/A',
        mktCap: 'ETF',
        high52: 427.63,
        low52: 331.20,
        rsi: 54.7,
        ivBase: 18.6,
        color: '#2dd4bf'
      }
    ];

    // Application State
    let currentPage = 'market'; // 'market' | 'analysis' | 'options'
    let selectedTicker = 'NVDA';
    let currentChartMode = 'price'; // 'price' | 'rsi' | 'volume' | 'ma' | 'bb'
    let selectedExpiryIdx = 0;
    let showNearMoneyOnly = false;
    let cachedSeries = {};
    let currentOptionsChain = [];

    const expirations = [
      { label: 'Nov 20, 2026', dte: 8, t: 8 / 365, ivMult: 1.04 },
      { label: 'Dec 18, 2026', dte: 36, t: 36 / 365, ivMult: 1.00 },
      { label: 'Jan 15, 2027', dte: 64, t: 64 / 365, ivMult: 0.97 },
      { label: 'Mar 19, 2027', dte: 127, t: 127 / 365, ivMult: 0.94 }
    ];

    // =========================================================================
    // 2. CUSTOM VECTOR BRAND LOGOS (Matches Screenshot 1 Icons)
    // =========================================================================
    function getCompanyLogoSVG(ticker) {
      switch (ticker) {
        case 'NVDA':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <path d="M3 12c4-5 14-5 18 0" stroke="#4ade80" stroke-width="2.3" stroke-linecap="round"/>
            <path d="M6 15c3-3.5 9-3.5 12 0" stroke="#22c55e" stroke-width="2.2" stroke-linecap="round"/>
            <circle cx="12" cy="17.5" r="2" fill="#86efac"/>
          </svg>`;
        case 'GOOGL':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24">
            <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3-3C17.2 1.9 14.8 1 12 1 7.7 1 4 3.5 2.2 7.1l3.5 2.7C6.6 7 9.1 5 12 5z"/>
            <path fill="#4285F4" d="M22.5 12.2c0-.8-.1-1.5-.2-2.2H12v4.3h5.9c-.3 1.4-1.1 2.6-2.3 3.4l3.5 2.7c2.1-1.9 3.4-4.8 3.4-8.2z"/>
            <path fill="#FBBC05" d="M5.7 14.2c-.2-.7-.4-1.4-.4-2.2s.2-1.5.4-2.2L2.2 7.1C1.4 8.6 1 10.2 1 12s.4 3.4 1.2 4.9l3.5-2.7z"/>
            <path fill="#34A853" d="M12 23c3 0 5.5-1 7.3-2.7l-3.5-2.7c-1 .7-2.2 1.1-3.8 1.1-2.9 0-5.4-2-6.3-4.6l-3.5 2.7C4 20.5 7.7 23 12 23z"/>
          </svg>`;
        case 'TSM':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9.5" stroke="#ef4444" stroke-width="2.2"/>
            <path d="M7 9h10M12 9v8" stroke="#ef4444" stroke-width="2.2" stroke-linecap="round"/>
          </svg>`;
        case 'AMD':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <path d="M5 19L18 6M10 6h8v8" stroke="#ef4444" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>`;
        case 'MSFT':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24">
            <rect x="3" y="3" width="8" height="8" fill="#f25022"/>
            <rect x="13" y="3" width="8" height="8" fill="#7fba00"/>
            <rect x="3" y="13" width="8" height="8" fill="#00a4ef"/>
            <rect x="13" y="13" width="8" height="8" fill="#ffb900"/>
          </svg>`;
        case 'META':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <path d="M4 14.5c0-3 2-5.5 4.2-5.5 2 0 3.2 1.8 3.8 3 .6-1.2 1.8-3 3.8-3 2.2 0 4.2 2.5 4.2 5.5 0 2.2-1.4 3.5-3.2 3.5-1.7 0-2.9-1.2-4.8-4.2-1.9 3-3.1 4.2-4.8 4.2C5.4 18 4 16.7 4 14.5z" stroke="#38bdf8" stroke-width="2.2"/>
          </svg>`;
        case 'AMZN':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <text x="7" y="14" fill="#ffffff" font-size="13" font-weight="800" font-family="Inter">a</text>
            <path d="M5 17.5c4.5 2.5 9.5 2.5 14 0" stroke="#f59e0b" stroke-width="2.1" stroke-linecap="round"/>
            <path d="M17 16l2.3 1.4-1.4 2.1" stroke="#f59e0b" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>`;
        case 'AAPL':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="#e2e8f0">
            <path d="M16.5 12.6c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.9-1.4-.1-2.8.8-3.5.8-.7 0-1.8-.8-3-.8-1.5 0-3 .9-3.8 2.3-1.6 2.8-.4 6.9 1.1 9.1.8 1.1 1.7 2.3 2.9 2.3 1.1 0 1.6-.7 3-.7 1.4 0 1.8.7 3 .7 1.2 0 2-1.1 2.8-2.2.9-1.3 1.2-2.5 1.3-2.6-.1-.1-2.4-.9-2.4-3.5zM14.2 5.6c.6-.8 1.1-1.8.9-2.9-.9 0-2 .6-2.6 1.4-.6.7-1.1 1.8-.9 2.8 1 .1 2-.5 2.6-1.3z"/>
          </svg>`;
        case 'ASML':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="8.5" stroke="#38bdf8" stroke-width="2.6"/>
            <circle cx="12" cy="12" r="3" fill="#0ea5e9"/>
          </svg>`;
        case 'TSLA':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <path d="M5 6.5c4.5-1.5 9.5-1.5 14 0M12 6v13M8 9.5h8" stroke="#ef4444" stroke-width="2.2" stroke-linecap="round"/>
          </svg>`;
        case 'VUAG.L':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <path d="M12 4L4 19h16L12 4z" stroke="#f43f5e" stroke-width="2.2" stroke-linejoin="round"/>
          </svg>`;
        case 'EQQQ.L':
          return `<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="8.5" stroke="#2dd4bf" stroke-width="2"/>
            <circle cx="12" cy="12" r="4.5" stroke="#38bdf8" stroke-width="1.8"/>
          </svg>`;
        default:
          return `<div class="w-5 h-5 rounded-md bg-blue-600/40 border border-blue-400/60 flex items-center justify-center text-[10px] font-extrabold text-blue-200 shrink-0">${ticker.slice(0, 2)}</div>`;
      }
    }

    function getRSIBadgeHTML(rsi) {
      let cls = 'bg-emerald-400 text-slate-950';
      if (rsi < 40) cls = 'bg-amber-300 text-slate-950';
      else if (rsi >= 70) cls = 'bg-rose-500 text-white';
      return `<span class="inline-block min-w-[46px] text-center px-2 py-0.5 rounded-md font-mono-num font-extrabold text-xs ${cls}">${rsi.toFixed(1)}</span>`;
    }

    // =========================================================================
    // 3. PAGE ROUTING & NAVIGATION
    // =========================================================================
    function switchPage(page) {
      currentPage = page;
      document.getElementById('page-market').classList.toggle('hidden', page !== 'market');
      document.getElementById('page-analysis').classList.toggle('hidden', page !== 'analysis');
      document.getElementById('page-options').classList.toggle('hidden', page !== 'options');

      // Update Nav Pill Styles
      const tabs = {
        market: document.getElementById('nav-market'),
        analysis: document.getElementById('nav-analysis'),
        options: document.getElementById('nav-options')
      };
      Object.entries(tabs).forEach(([key, el]) => {
        if (!el) return;
        if (key === page) {
          el.classList.add('btn-royal', 'text-white');
          el.classList.remove('text-blue-200/90', 'hover:bg-blue-900/40');
        } else {
          el.classList.remove('btn-royal', 'text-white');
          el.classList.add('text-blue-200/90', 'hover:bg-blue-900/40');
        }
      });

      syncCompanyDropdowns();

      if (page === 'analysis') {
        renderStockAnalysis();
      } else if (page === 'options') {
        renderOptionsPage();
      } else {
        renderMarketWatchTable();
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function selectCompanyAndOpenAnalysis(ticker) {
      selectedTicker = ticker;
      switchPage('analysis');
    }

    function openSelectedAnalysis() {
      switchPage('analysis');
    }

    function openSelectedOptions() {
      switchPage('options');
    }

    function handleSelectCompany(ticker) {
      selectedTicker = ticker;
      syncCompanyDropdowns();
      if (currentPage === 'analysis') renderStockAnalysis();
      if (currentPage === 'options') renderOptionsPage();
    }

    function syncCompanyDropdowns() {
      const optionsHTML = stocksData
        .map(s => `<option value="${s.ticker}" ${s.ticker === selectedTicker ? 'selected' : ''}>${s.ticker} - ${s.name}</option>`)
        .join('');
      const sel1 = document.getElementById('analysis-company-select');
      const sel2 = document.getElementById('options-company-select');
      if (sel1) sel1.innerHTML = optionsHTML;
      if (sel2) sel2.innerHTML = optionsHTML;
    }

    // =========================================================================
    // 4. PAGE 1: MARKET WATCH RENDERING & INTERACTIONS
    // =========================================================================
    function renderMarketWatchTable() {
      const tbody = document.getElementById('market-watch-tbody');
      let gainers = 0;
      let losers = 0;

      tbody.innerHTML = stocksData.map(stock => {
        const isPos = stock.change >= 0;
        if (isPos) gainers++;
        else losers++;

        const chgColor = isPos ? 'text-emerald-400' : 'text-rose-400';
        const chgSign = isPos ? '+' : '';
        const peDisplay = stock.pe === 'None'
          ? `<span class="text-blue-400/80 font-semibold">None</span>`
          : `<span class="text-white">${stock.pe}</span>`;
        const isSelectedRow = stock.ticker === selectedTicker ? 'ring-1 ring-inset ring-blue-400/70 !bg-blue-900/35' : '';

        return `
          <tr onclick="selectCompanyAndOpenAnalysis('${stock.ticker}')" class="${isSelectedRow}" title="Click to inspect ${stock.name} Analysis & Options">
            <td class="pl-3.5">
              <div class="flex items-center gap-2.5">
                ${getCompanyLogoSVG(stock.ticker)}
                <span class="font-extrabold text-white tracking-wide">${stock.ticker}</span>
              </div>
            </td>
            <td class="text-right font-mono-num font-bold text-white">${stock.today.toFixed(2)}</td>
            <td class="text-right font-mono-num text-blue-100/90">${stock.yesterday.toFixed(2)}</td>
            <td class="text-right font-mono-num font-bold ${chgColor}">${chgSign}${stock.change.toFixed(2)}</td>
            <td class="text-right font-mono-num font-bold ${chgColor}">${chgSign}${stock.pctChange.toFixed(2)}%</td>
            <td class="text-right font-mono-num text-blue-100">${stock.ma20.toFixed(2)}</td>
            <td class="text-right font-mono-num text-blue-100">${stock.ma50.toFixed(2)}</td>
            <td class="text-right font-mono-num text-blue-100">${stock.ma200.toFixed(2)}</td>
            <td class="text-right font-mono-num">${peDisplay}</td>
            <td class="text-right font-mono-num text-white">${stock.high52.toFixed(2)}</td>
            <td class="text-right font-mono-num text-white">${stock.low52.toFixed(2)}</td>
            <td class="text-center">${getRSIBadgeHTML(stock.rsi)}</td>
            <td class="text-center" onclick="event.stopPropagation(); removeStock('${stock.ticker}')">
              <button title="Remove ${stock.ticker}" class="p-1.5 rounded-md text-rose-500 hover:bg-rose-500/20 hover:text-rose-300 transition">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clip-rule="evenodd"/>
                </svg>
              </button>
            </td>
          </tr>
        `;
      }).join('');

      document.getElementById('gainers-count').textContent = `${gainers} ${gainers === 1 ? 'Gainer' : 'Gainers'}`;
      document.getElementById('losers-count').textContent = `${losers} ${losers === 1 ? 'Loser' : 'Losers'}`;
      document.getElementById('total-count').textContent = `Total: ${stocksData.length}`;
    }

    function handleAddTicker() {
      const input = document.getElementById('ticker-input');
      const raw = input.value.trim().toUpperCase();
      if (!raw) {
        showToast('Enter a valid ticker symbol (e.g. NFLX, ARM, PLTR).', true);
        return;
      }
      if (stocksData.some(s => s.ticker === raw)) {
        selectedTicker = raw;
        renderMarketWatchTable();
        showToast(`${raw} is already in your Market Watch list.`);
        input.value = '';
        return;
      }

      // Preset realistic profiles for common symbols or procedural generator
      const presets = {
        NFLX: { name: 'Netflix Inc.', today: 842.50, yesterday: 825.10, pe: '44.20', eps: '19.06', mktCap: '361.2B', rsi: 63.4, ivBase: 35.5 },
        PLTR: { name: 'Palantir Technologies', today: 68.40, yesterday: 64.15, pe: '142.50', eps: '0.48', mktCap: '154.8B', rsi: 71.2, ivBase: 62.0 },
        ARM:  { name: 'Arm Holdings plc', today: 164.80, yesterday: 159.20, pe: '88.40', eps: '1.86', mktCap: '173.4B', rsi: 56.8, ivBase: 51.4 },
        AVGO: { name: 'Broadcom Inc.', today: 214.65, yesterday: 208.90, pe: '34.12', eps: '6.29', mktCap: '1.01T', rsi: 60.5, ivBase: 39.0 }
      };

      const p = presets[raw];
      const basePrice = p ? p.today : +(85 + Math.random() * 340).toFixed(2);
      const yestPrice = p ? p.yesterday : +(basePrice * (1 + (Math.random() - 0.52) * 0.05)).toFixed(2);
      const change = +(basePrice - yestPrice).toFixed(2);
      const pctChange = +((change / yestPrice) * 100).toFixed(2);

      stocksData.push({
        ticker: raw,
        name: p ? p.name : `${raw} Holdings Corp.`,
        today: basePrice,
        yesterday: yestPrice,
        change,
        pctChange,
        ma20: +(basePrice * 0.985).toFixed(2),
        ma50: +(basePrice * 0.955).toFixed(2),
        ma200: +(basePrice * 0.89).toFixed(2),
        pe: p ? p.pe : (18 + Math.random() * 28).toFixed(2),
        eps: p ? p.eps : (basePrice / 24).toFixed(2),
        mktCap: p ? p.mktCap : `${(basePrice * 1.4).toFixed(1)}B`,
        high52: +(basePrice * 1.18).toFixed(2),
        low52: +(basePrice * 0.62).toFixed(2),
        rsi: p ? p.rsi : +(42 + Math.random() * 28).toFixed(1),
        ivBase: p ? p.ivBase : +(28 + Math.random() * 25).toFixed(1),
        color: '#38bdf8'
      });

      selectedTicker = raw;
      input.value = '';
      renderMarketWatchTable();
      syncCompanyDropdowns();
      showToast(`Added ${raw} to Market Watch.`);
    }

    function removeStock(ticker) {
      if (stocksData.length <= 1) {
        showToast('At least one symbol must remain in Market Watch.', true);
        return;
      }
      const idx = stocksData.findIndex(s => s.ticker === ticker);
      if (idx !== -1) {
        stocksData.splice(idx, 1);
        if (selectedTicker === ticker) selectedTicker = stocksData[0].ticker;
        renderMarketWatchTable();
        syncCompanyDropdowns();
        showToast(`Removed ${ticker} from Market Watch.`);
      }
    }

    function handleUpdateAllSymbols() {
      const icon = document.getElementById('refresh-all-icon');
      icon.classList.remove('spin-refresh');
      void icon.offsetWidth;
      icon.classList.add('spin-refresh');

      stocksData.forEach(s => {
        const delta = s.today * ((Math.random() - 0.48) * 0.008);
        s.today = +(s.today + delta).toFixed(2);
        s.change = +(s.today - s.yesterday).toFixed(2);
        s.pctChange = +((s.change / s.yesterday) * 100).toFixed(2);
        s.rsi = +Math.min(82, Math.max(25, s.rsi + (Math.random() - 0.5) * 1.2)).toFixed(1);
      });
      cachedSeries = {}; // Regenerate chart series with latest tick
      renderMarketWatchTable();
      if (currentPage === 'analysis') renderStockAnalysis();
      if (currentPage === 'options') renderOptionsPage();
      showToast('All market quotes & technical indicators refreshed.');
    }

    // =========================================================================
    // 5. PAGE 2: STOCK ANALYSIS (Chart, Price Ladder, Key Data)
    // =========================================================================
    function getStockByTicker(ticker) {
      return stocksData.find(s => s.ticker === ticker) || stocksData[0];
    }

    function generateHistoricalSeries(stock) {
      if (cachedSeries[stock.ticker]) return cachedSeries[stock.ticker];

      // Deterministic pseudo-random generator seeded by ticker string
      let seed = stock.ticker.split('').reduce((acc, c) => acc + c.charCodeAt(0) * 17, 101);
      const rand = () => {
        seed = (seed * 9301 + 49297) % 233280;
        return seed / 233280;
      };

      const totalBars = 92; // Jul 2026 -> Nov 2026
      const bars = [];
      let price = stock.low52 * 1.15;
      const targetEnd = stock.today;

      for (let i = 0; i < totalBars; i++) {
        const progress = i / (totalBars - 1);
        const trendTarget = price + ((targetEnd - price) / (totalBars - i)) * 0.42;
        const wave = Math.sin(i * 0.24) * (targetEnd * 0.028);
        const noise = (rand() - 0.48) * (targetEnd * 0.032);
        const open = i === 0 ? price : bars[i - 1].close;
        let close = i === totalBars - 1 ? targetEnd : trendTarget + wave * 0.25 + noise;
        close = Math.max(stock.low52 * 0.9, close);

        const high = Math.max(open, close) + rand() * (targetEnd * 0.022);
        const low = Math.min(open, close) - rand() * (targetEnd * 0.022);
        const volume = Math.round((28 + rand() * 55) * 1000000);

        bars.push({ open, high, low, close, volume });
        price = close;
      }

      // Compute MA20, MA50, MA200, Bollinger Bands, and RSI series aligned with stock's metrics
      for (let i = 0; i < totalBars; i++) {
        const ratio = i / (totalBars - 1);
        const slice20 = bars.slice(Math.max(0, i - 19), i + 1);
        const rawMa20 = slice20.reduce((a, b) => a + b.close, 0) / slice20.length;
        bars[i].ma20 = rawMa20 * (1 - ratio * 0.15) + stock.ma20 * (ratio * 0.15);

        const slice50 = bars.slice(Math.max(0, i - 44), i + 1);
        const rawMa50 = slice50.reduce((a, b) => a + b.close, 0) / slice50.length;
        bars[i].ma50 = rawMa50 * (1 - ratio * 0.25) + stock.ma50 * (ratio * 0.25);

        bars[i].ma200 = stock.ma200 * (0.74 + 0.26 * ratio);

        const std = bars[i].ma20 * 0.048;
        bars[i].bbUpper = bars[i].ma20 + 2 * std;
        bars[i].bbLower = bars[i].ma20 - 2 * std;
        bars[i].rsi = Math.min(82, Math.max(24, stock.rsi + Math.sin(i * 0.35) * 14 * (1 - ratio * 0.7)));
      }

      cachedSeries[stock.ticker] = bars;
      return bars;
    }

    function setChartMode(mode) {
      currentChartMode = mode;
      document.querySelectorAll('.chart-mode-btn').forEach(btn => {
        btn.classList.remove('btn-royal', 'text-white');
        btn.classList.add('text-blue-200', 'hover:bg-blue-900/50');
      });
      const activeBtn = document.getElementById(`tab-chart-${mode}`);
      if (activeBtn) {
        activeBtn.classList.add('btn-royal', 'text-white');
        activeBtn.classList.remove('text-blue-200', 'hover:bg-blue-900/50');
      }
      drawStockChart();
    }

    function renderStockAnalysis() {
      const stock = getStockByTicker(selectedTicker);

      // 1. Render Price Level Ladder (+30% down to -30%)
      const levels = [30, 25, 20, 15, 10, 5, 0, -5, -10, -15, -20, -25, -30];
      const ladderEl = document.getElementById('price-level-list');
      ladderEl.innerHTML = levels.map(pct => {
        const levelPrice = stock.today * (1 + pct / 100);
        if (pct === 0) {
          return `
            <div class="px-4 py-1.5 bg-amber-400/20 border-y border-amber-400/70 flex items-center justify-between font-extrabold text-amber-300">
              <span>CURRENT</span>
              <span>${stock.today.toFixed(2)}</span>
            </div>
          `;
        }
        const label = pct > 0 ? `+${pct}%` : `${pct}%`;
        const textTint = pct > 0 ? 'text-blue-100' : 'text-blue-200/90';
        return `
          <div class="px-4 py-1.5 hover:bg-blue-900/40 flex items-center justify-between ${textTint} transition">
            <span class="font-semibold">${label}</span>
            <span class="font-bold text-white">${levelPrice.toFixed(2)}</span>
          </div>
        `;
      }).join('');

      // 2. Render Bottom KEY DATA Panel
      const isPos = stock.change >= 0;
      const sign = isPos ? '+' : '';
      const chgCls = isPos ? 'text-emerald-400' : 'text-rose-400';

      document.getElementById('kd-current-price').textContent = stock.today.toFixed(2);
      const chgEl = document.getElementById('kd-price-change');
      chgEl.textContent = `${sign}${stock.change.toFixed(2)}  ${sign}${stock.pctChange.toFixed(2)}%`;
      chgEl.className = `ml-2 text-xs font-bold ${chgCls}`;

      document.getElementById('kd-day-high').textContent = (stock.today * 1.018).toFixed(2);
      document.getElementById('kd-day-low').textContent = (stock.today * 0.984).toFixed(2);
      document.getElementById('kd-52-high').textContent = stock.high52.toFixed(2);
      document.getElementById('kd-52-low').textContent = stock.low52.toFixed(2);
      document.getElementById('kd-mkt-cap').textContent = stock.mktCap;
      document.getElementById('kd-pe-ratio').textContent = stock.pe;
      document.getElementById('kd-eps').textContent = stock.eps;

      const rsiBadge = document.getElementById('kd-rsi-badge');
      rsiBadge.textContent = stock.rsi.toFixed(1);
      rsiBadge.className = `font-mono-num font-extrabold px-3 py-0.5 rounded-md text-xs ${
        stock.rsi < 40 ? 'bg-amber-300 text-slate-950' : stock.rsi >= 70 ? 'bg-rose-500 text-white' : 'bg-emerald-400 text-slate-950'
      }`;

      // 3. Draw Canvas Chart
      requestAnimationFrame(drawStockChart);
    }

    function drawStockChart(hoverIndex = -1) {
      const canvas = document.getElementById('stock-chart-canvas');
      const container = document.getElementById('chart-container');
      if (!canvas || !container || container.clientWidth === 0) return;

      const dpr = window.devicePixelRatio || 1;
      const width = container.clientWidth;
      const height = container.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;

      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);

      const stock = getStockByTicker(selectedTicker);
      const bars = generateHistoricalSeries(stock);

      // Background
      ctx.fillStyle = '#04102b';
      ctx.fillRect(0, 0, width, height);

      const padLeft = 52;
      const padRight = 16;
      const padTop = 16;
      const padBottom = 28;
      const plotW = width - padLeft - padRight;
      const plotH = height - padTop - padBottom;

      // Determine Y-Axis Min/Max based on mode
      let yMin, yMax;
      if (currentChartMode === 'rsi') {
        yMin = 15;
        yMax = 90;
      } else if (currentChartMode === 'volume') {
        yMin = 0;
        yMax = Math.max(...bars.map(b => b.volume)) * 1.15;
      } else {
        const allVals = bars.flatMap(b => [b.high, b.low, b.ma20, b.ma50, b.ma200]);
        if (currentChartMode === 'bb') {
          allVals.push(...bars.map(b => b.bbUpper), ...bars.map(b => b.bbLower));
        }
        const rawMin = Math.min(...allVals);
        const rawMax = Math.max(...allVals);
        const margin = (rawMax - rawMin) * 0.08;
        yMin = rawMin - margin;
        yMax = rawMax + margin;
      }

      const toX = idx => padLeft + (idx / (bars.length - 1)) * plotW;
      const toY = val => padTop + plotH - ((val - yMin) / (yMax - yMin)) * plotH;

      // Horizontal Grid & Y Labels
      ctx.strokeStyle = 'rgba(37, 99, 235, 0.25)';
      ctx.lineWidth = 1;
      ctx.fillStyle = '#cbd5e1';
      ctx.font = '600 11px "JetBrains Mono", monospace';
      ctx.textAlign = 'right';

      const gridRows = 6;
      for (let r = 0; r <= gridRows; r++) {
        const val = yMin + (r / gridRows) * (yMax - yMin);
        const y = toY(val);
        ctx.beginPath();
        ctx.moveTo(padLeft, y);
        ctx.lineTo(width - padRight, y);
        ctx.stroke();

        const label = currentChartMode === 'volume'
          ? `${(val / 1e6).toFixed(0)}M`
          : currentChartMode === 'rsi'
            ? val.toFixed(0)
            : val >= 1000 ? val.toFixed(0) : val.toFixed(0);
        ctx.fillText(label, padLeft - 8, y + 4);
      }

      // Vertical Grid & Month Labels (Jul 2026 -> Nov 2026)
      const monthLabels = [
        { idx: 4, text: 'Jul 2026' },
        { idx: 24, text: 'Aug 2026' },
        { idx: 46, text: 'Sep 2026' },
        { idx: 68, text: 'Oct 2026' },
        { idx: 86, text: 'Nov 2026' }
      ];
      ctx.textAlign = 'center';
      monthLabels.forEach(m => {
        const x = toX(m.idx);
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.28)';
        ctx.beginPath();
        ctx.moveTo(x, padTop);
        ctx.lineTo(x, height - padBottom);
        ctx.stroke();
        ctx.fillStyle = '#e2e8f0';
        ctx.fillText(m.text, x, height - 8);
      });

      // Helper to draw smooth line
      const drawLine = (key, color, lineWidth = 1.8) => {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.beginPath();
        bars.forEach((b, i) => {
          const x = toX(i);
          const y = toY(b[key]);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
      };

      if (currentChartMode === 'rsi') {
        // Overbought / Oversold dashed zones
        [70, 30].forEach(lvl => {
          ctx.save();
          ctx.setLineDash([4, 4]);
          ctx.strokeStyle = lvl === 70 ? '#f87171' : '#facc15';
          ctx.beginPath();
          ctx.moveTo(padLeft, toY(lvl));
          ctx.lineTo(width - padRight, toY(lvl));
          ctx.stroke();
          ctx.restore();
        });
        drawLine('rsi', '#38bdf8', 2.4);
      } else if (currentChartMode === 'volume') {
        const barW = Math.max(2, (plotW / bars.length) * 0.62);
        bars.forEach((b, i) => {
          const x = toX(i) - barW / 2;
          const y = toY(b.volume);
          ctx.fillStyle = b.close >= b.open ? 'rgba(34, 197, 94, 0.85)' : 'rgba(239, 68, 68, 0.85)';
          ctx.fillRect(x, y, barW, padTop + plotH - y);
        });
      } else {
        // Draw Bollinger Band Shading if active
        if (currentChartMode === 'bb') {
          ctx.fillStyle = 'rgba(56, 189, 248, 0.12)';
          ctx.beginPath();
          bars.forEach((b, i) => {
            const x = toX(i);
            const y = toY(b.bbUpper);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          });
          for (let i = bars.length - 1; i >= 0; i--) {
            ctx.lineTo(toX(i), toY(bars[i].bbLower));
          }
          ctx.closePath();
          ctx.fill();
          drawLine('bbUpper', '#38bdf8', 1.3);
          drawLine('bbLower', '#38bdf8', 1.3);
        }

        // Draw Candlesticks (unless MA-only mode)
        if (currentChartMode !== 'ma') {
          const candleW = Math.max(2.2, (plotW / bars.length) * 0.56);
          bars.forEach((b, i) => {
            const x = toX(i);
            const isUp = b.close >= b.open;
            const col = isUp ? '#22c55e' : '#ef4444';

            // Wick
            ctx.strokeStyle = col;
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(x, toY(b.high));
            ctx.lineTo(x, toY(b.low));
            ctx.stroke();

            // Body
            const top = toY(Math.max(b.open, b.close));
            const bot = toY(Math.min(b.open, b.close));
            ctx.fillStyle = col;
            ctx.fillRect(x - candleW / 2, top, candleW, Math.max(1.8, bot - top));
          });
        } else {
          drawLine('close', '#ffffff', 2);
        }

        // Draw MA20 (Yellow), MA50 (Sky Blue), MA200 (Magenta)
        drawLine('ma20', '#facc15', 1.9);
        drawLine('ma50', '#38bdf8', 1.9);
        drawLine('ma200', '#e879f9', 1.9);
      }

      // Hover Crosshair
      if (hoverIndex >= 0 && hoverIndex < bars.length) {
        const hx = toX(hoverIndex);
        ctx.save();
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = 'rgba(255,255,255,0.65)';
        ctx.beginPath();
        ctx.moveTo(hx, padTop);
        ctx.lineTo(hx, padTop + plotH);
        ctx.stroke();
        ctx.restore();
      }
    }

    // Canvas Mouse/Touch Hover Crosshair Listener
    (function attachChartHover() {
      const canvas = document.getElementById('stock-chart-canvas');
      const tooltip = document.getElementById('chart-tooltip');
      if (!canvas) return;

      const handleMove = clientX => {
        const rect = canvas.getBoundingClientRect();
        const relX = clientX - rect.left - 52;
        const plotW = rect.width - 68;
        if (relX < 0 || relX > plotW) {
          tooltip.classList.add('hidden');
          drawStockChart(-1);
          return;
        }
        const stock = getStockByTicker(selectedTicker);
        const bars = generateHistoricalSeries(stock);
        const idx = Math.min(bars.length - 1, Math.max(0, Math.round((relX / plotW) * (bars.length - 1))));
        const b = bars[idx];

        tooltip.classList.remove('hidden');
        tooltip.innerHTML = `
          <span class="text-blue-300 font-bold">${stock.ticker}</span> &nbsp;
          O: <span class="text-white">${b.open.toFixed(2)}</span> &nbsp;
          H: <span class="text-emerald-400">${b.high.toFixed(2)}</span> &nbsp;
          L: <span class="text-rose-400">${b.low.toFixed(2)}</span> &nbsp;
          C: <span class="text-amber-300 font-bold">${b.close.toFixed(2)}</span> &nbsp;
          <span class="text-yellow-300">MA20: ${b.ma20.toFixed(1)}</span>
        `;
        drawStockChart(idx);
      };

      canvas.addEventListener('mousemove', e => handleMove(e.clientX));
      canvas.addEventListener('mouseleave', () => {
        tooltip.classList.add('hidden');
        drawStockChart(-1);
      });
    })();

    function runAnalyzeEffect() {
      const stock = getStockByTicker(selectedTicker);
      cachedSeries[stock.ticker] = null;
      renderStockAnalysis();
      showToast(`Quantitative technical scan updated for ${stock.ticker}.`);
    }

    // =========================================================================
    // 6. PAGE 3: PUT & CALL OPTION DATA (Black-Scholes Approximation & Chain)
    // =========================================================================
    function setOptionExpiry(idx) {
      selectedExpiryIdx = idx;
      document.querySelectorAll('.exp-pill').forEach((btn, i) => {
        if (i === idx) {
          btn.classList.add('btn-royal', 'text-white');
          btn.classList.remove('text-blue-200', 'hover:bg-blue-900/40');
        } else {
          btn.classList.remove('btn-royal', 'text-white');
          btn.classList.add('text-blue-200', 'hover:bg-blue-900/40');
        }
      });
      renderOptionsPage();
    }

    function toggleStrikeRange() {
      showNearMoneyOnly = !showNearMoneyOnly;
      document.getElementById('strike-range-btn').textContent = showNearMoneyOnly
        ? 'Range: Near ATM (±15%)'
        : 'Range: All Strikes';
      renderOptionsPage();
    }

    // Standard Normal CDF approximation for Black-Scholes Greeks & Pricing
    function normCDF(x) {
      const t = 1 / (1 + 0.2316419 * Math.abs(x));
      const d = 0.3989423 * Math.exp(-x * x / 2);
      const prob = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
      return x > 0 ? 1 - prob : prob;
    }

    function buildOptionsChain(stock, exp) {
      const spot = stock.today;
      const step = spot < 150 ? 2.5 : spot < 450 ? 5 : spot < 900 ? 10 : 25;
      const atmStrike = Math.round(spot / step) * step;
      const strikes = [];
      for (let i = -7; i <= 7; i++) {
        const k = +(atmStrike + i * step).toFixed(2);
        if (k > 0) strikes.push(k);
      }

      const r = 0.042;
      const baseVol = (stock.ivBase / 100) * exp.ivMult;

      return strikes.map((strike, idx) => {
        const moneyness = (strike - spot) / spot;
        // Volatility smile skew (higher IV on OTM puts)
        const iv = Math.max(0.12, baseVol + Math.pow(moneyness, 2) * 0.65 - moneyness * 0.14);
        const sqrtT = Math.sqrt(exp.t);
        const d1 = (Math.log(spot / strike) + (r + 0.5 * iv * iv) * exp.t) / (iv * sqrtT);
        const d2 = d1 - iv * sqrtT;

        const callPrice = Math.max(0.05, spot * normCDF(d1) - strike * Math.exp(-r * exp.t) * normCDF(d2));
        const putPrice = Math.max(0.05, strike * Math.exp(-r * exp.t) * normCDF(-d2) - spot * normCDF(-d1));

        const callDelta = normCDF(d1);
        const putDelta = callDelta - 1;
        const gamma = Math.exp(-0.5 * d1 * d1) / (Math.sqrt(2 * Math.PI) * spot * iv * sqrtT);
        const vega = (spot * sqrtT * Math.exp(-0.5 * d1 * d1) / Math.sqrt(2 * Math.PI)) / 100;
        const callTheta = (-spot * iv * Math.exp(-0.5 * d1 * d1) / (2 * Math.sqrt(2 * Math.PI) * sqrtT)) / 365;
        const putTheta = callTheta * 0.92;

        // Realistic OI and Volume concentration around ATM
        const prox = Math.exp(-Math.pow(moneyness * 7, 2));
        const callOI = Math.round((1800 + prox * 24500) * (1 + (idx % 3) * 0.18));
        const callVol = Math.round(callOI * (0.28 + prox * 0.35));
        const putOI = Math.round((1600 + prox * 21200) * (1 + ((idx + 1) % 3) * 0.16));
        const putVol = Math.round(putOI * (0.25 + prox * 0.32));

        const spreadC = Math.max(0.02, callPrice * 0.018);
        const spreadP = Math.max(0.02, putPrice * 0.018);

        return {
          strike,
          isATM: strike === atmStrike,
          call: {
            oi: callOI,
            vol: callVol,
            iv: +(iv * 100).toFixed(1),
            delta: +callDelta.toFixed(3),
            gamma: +gamma.toFixed(4),
            theta: +callTheta.toFixed(3),
            vega: +vega.toFixed(3),
            bid: +Math.max(0.01, callPrice - spreadC).toFixed(2),
            ask: +(callPrice + spreadC).toFixed(2),
            last: +callPrice.toFixed(2),
            pctChg: +(stock.pctChange * (1.8 + Math.abs(callDelta) * 2.4)).toFixed(1),
            itm: spot > strike
          },
          put: {
            oi: putOI,
            vol: putVol,
            iv: +((iv + 0.012) * 100).toFixed(1),
            delta: +putDelta.toFixed(3),
            gamma: +gamma.toFixed(4),
            theta: +putTheta.toFixed(3),
            vega: +vega.toFixed(3),
            bid: +Math.max(0.01, putPrice - spreadP).toFixed(2),
            ask: +(putPrice + spreadP).toFixed(2),
            last: +putPrice.toFixed(2),
            pctChg: +(-stock.pctChange * (1.7 + Math.abs(putDelta) * 2.2)).toFixed(1),
            itm: spot < strike
          }
        };
      });
    }

    function renderOptionsPage() {
      const stock = getStockByTicker(selectedTicker);
      const exp = expirations[selectedExpiryIdx];
      const chain = buildOptionsChain(stock, exp);
      currentOptionsChain = chain;

      // Update Summary Cards
      const isPos = stock.change >= 0;
      const sign = isPos ? '+' : '';
      document.getElementById('opt-spot-price').textContent = `$${stock.today.toFixed(2)}`;
      const spotChgEl = document.getElementById('opt-spot-change');
      spotChgEl.textContent = `${sign}${stock.change.toFixed(2)} (${sign}${stock.pctChange.toFixed(2)}%)`;
      spotChgEl.className = `text-xs font-mono-num font-bold ${isPos ? 'text-emerald-400' : 'text-rose-400'}`;

      const iv30 = +(stock.ivBase * exp.ivMult).toFixed(1);
      document.getElementById('opt-iv-val').textContent = `${iv30}%`;
      document.getElementById('opt-iv-rank').textContent = `IV Rank: ${Math.min(96, Math.round(iv30 * 1.35))}`;
      document.getElementById('opt-hv-val').textContent = `${(iv30 * 0.84).toFixed(1)}%`;

      const totalCallVol = chain.reduce((s, r) => s + r.call.vol, 0);
      const totalPutVol = chain.reduce((s, r) => s + r.put.vol, 0);
      const pcr = +(totalPutVol / Math.max(1, totalCallVol)).toFixed(2);
      document.getElementById('opt-pcr-val').textContent = pcr.toFixed(2);
      document.getElementById('opt-call-vol').textContent = `${(totalCallVol / 1000).toFixed(1)}K`;
      document.getElementById('opt-put-vol').textContent = `${(totalPutVol / 1000).toFixed(1)}K`;

      const sentBadge = document.getElementById('opt-sentiment-badge');
      if (pcr < 0.85) {
        sentBadge.textContent = 'Bullish Call Flow';
        sentBadge.className = 'px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/40';
      } else {
        sentBadge.textContent = 'Defensive Put Hedge';
        sentBadge.className = 'px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-400/40';
      }

      const atmRow = chain.find(r => r.isATM) || chain[Math.floor(chain.length / 2)];
      const expMoveDollar = +((atmRow.call.last + atmRow.put.last) * 0.85).toFixed(2);
      const expMovePct = +((expMoveDollar / stock.today) * 100).toFixed(2);
      document.getElementById('opt-max-pain').textContent = `$${atmRow.strike.toFixed(2)}`;
      document.getElementById('opt-exp-move').textContent = `±$${expMoveDollar.toFixed(2)} (±${expMovePct}%)`;

      // Filter strikes if Near ATM toggled
      const visibleRows = showNearMoneyOnly
        ? chain.filter(r => Math.abs((r.strike - stock.today) / stock.today) <= 0.15)
        : chain;

      const tbody = document.getElementById('options-chain-tbody');
      tbody.innerHTML = visibleRows.map((row, rIdx) => {
        const c = row.call;
        const p = row.put;
        const cChgCls = c.pctChg >= 0 ? 'text-emerald-400' : 'text-rose-400';
        const pChgCls = p.pctChg >= 0 ? 'text-emerald-400' : 'text-rose-400';
        const cCellBg = c.itm ? 'itm-call' : '';
        const pCellBg = p.itm ? 'itm-put' : '';
        const atmBanner = row.isATM
          ? `border-y-2 border-amber-400/90`
          : '';

        return `
          <tr class="${atmBanner}">
            <!-- CALLS -->
            <td onclick="openOptionModal(${row.strike}, 'CALL')" class="text-right font-mono-num text-blue-200 ${cCellBg}">${c.oi.toLocaleString()}</td>
            <td onclick="openOptionModal(${row.strike}, 'CALL')" class="text-right font-mono-num text-white ${cCellBg}">${c.vol.toLocaleString()}</td>
            <td onclick="openOptionModal(${row.strike}, 'CALL')" class="text-right font-mono-num text-cyan-300 ${cCellBg}">${c.iv.toFixed(1)}%</td>
            <td onclick="openOptionModal(${row.strike}, 'CALL')" class="text-right font-mono-num text-blue-100 ${cCellBg}">${c.delta.toFixed(2)}</td>
            <td onclick="openOptionModal(${row.strike}, 'CALL')" class="text-right font-mono-num text-emerald-300 font-semibold ${cCellBg}">${c.bid.toFixed(2)}</td>
            <td onclick="openOptionModal(${row.strike}, 'CALL')" class="text-right font-mono-num text-emerald-300 font-semibold ${cCellBg}">${c.ask.toFixed(2)}</td>
            <td onclick="openOptionModal(${row.strike}, 'CALL')" class="text-right font-mono-num font-extrabold text-white ${cCellBg}">${c.last.toFixed(2)}</td>
            <td onclick="openOptionModal(${row.strike}, 'CALL')" class="text-right font-mono-num font-bold ${cChgCls} ${cCellBg}">${c.pctChg >= 0 ? '+' : ''}${c.pctChg.toFixed(1)}%</td>

            <!-- CENTER STRIKE SPINE -->
            <td class="text-center font-mono-num font-extrabold text-sm px-3 ${row.isATM ? '!bg-amber-400/25 !text-amber-300' : '!bg-[#0c2763] !text-white'}">
              ${row.strike.toFixed(2)}
              ${row.isATM ? '<span class="block text-[9px] uppercase tracking-wider text-amber-300">ATM SPOT</span>' : ''}
            </td>

            <!-- PUTS -->
            <td onclick="openOptionModal(${row.strike}, 'PUT')" class="text-right font-mono-num font-bold ${pChgCls} ${pCellBg}">${p.pctChg >= 0 ? '+' : ''}${p.pctChg.toFixed(1)}%</td>
            <td onclick="openOptionModal(${row.strike}, 'PUT')" class="text-right font-mono-num font-extrabold text-white ${pCellBg}">${p.last.toFixed(2)}</td>
            <td onclick="openOptionModal(${row.strike}, 'PUT')" class="text-right font-mono-num text-rose-300 font-semibold ${pCellBg}">${p.bid.toFixed(2)}</td>
            <td onclick="openOptionModal(${row.strike}, 'PUT')" class="text-right font-mono-num text-rose-300 font-semibold ${pCellBg}">${p.ask.toFixed(2)}</td>
            <td onclick="openOptionModal(${row.strike}, 'PUT')" class="text-right font-mono-num text-blue-100 ${pCellBg}">${p.delta.toFixed(2)}</td>
            <td onclick="openOptionModal(${row.strike}, 'PUT')" class="text-right font-mono-num text-cyan-300 ${pCellBg}">${p.iv.toFixed(1)}%</td>
            <td onclick="openOptionModal(${row.strike}, 'PUT')" class="text-right font-mono-num text-white ${pCellBg}">${p.vol.toLocaleString()}</td>
            <td onclick="openOptionModal(${row.strike}, 'PUT')" class="text-right font-mono-num text-blue-200 ${pCellBg}">${p.oi.toLocaleString()}</td>
          </tr>
        `;
      }).join('');
    }

    // =========================================================================
    // 7. OPTION CONTRACT PAYOFF & GREEKS MODAL INSPECTOR
    // =========================================================================
    function openOptionModal(strike, type) {
      const stock = getStockByTicker(selectedTicker);
      const exp = expirations[selectedExpiryIdx];
      const row = currentOptionsChain.find(r => r.strike === strike);
      if (!row) return;

      const opt = type === 'CALL' ? row.call : row.put;
      const mark = +((opt.bid + opt.ask) / 2).toFixed(2);
      const breakeven = type === 'CALL' ? +(strike + mark).toFixed(2) : +(strike - mark).toFixed(2);
      const pop = Math.min(88, Math.max(12, Math.round((1 - Math.abs(opt.delta)) * 100)));

      const badge = document.getElementById('modal-contract-badge');
      badge.textContent = type;
      badge.className = `px-2.5 py-0.5 rounded text-xs font-extrabold uppercase ${
        type === 'CALL' ? 'bg-emerald-400 text-slate-950' : 'bg-rose-500 text-white'
      }`;

      document.getElementById('modal-contract-title').textContent =
        `${stock.ticker} $${strike.toFixed(2)} ${type === 'CALL' ? 'Call' : 'Put'} — ${exp.label}`;
      document.getElementById('modal-mark').textContent = `$${mark.toFixed(2)}`;
      document.getElementById('modal-breakeven').textContent = `$${breakeven.toFixed(2)}`;
      document.getElementById('modal-iv').textContent = `${opt.iv.toFixed(1)}%`;
      document.getElementById('modal-pop').textContent = `${pop}%`;

      document.getElementById('modal-delta').textContent = opt.delta.toFixed(3);
      document.getElementById('modal-gamma').textContent = opt.gamma.toFixed(4);
      document.getElementById('modal-theta').textContent = opt.theta.toFixed(3);
      document.getElementById('modal-vega').textContent = opt.vega.toFixed(3);
      document.getElementById('modal-oi').textContent = opt.oi.toLocaleString();
      document.getElementById('modal-max-loss').textContent = `Max Premium Risk: -$${(mark * 100).toFixed(2)}`;

      const modal = document.getElementById('option-modal');
      modal.classList.remove('hidden');
      modal.classList.add('flex');

      requestAnimationFrame(() => drawPayoffDiagram(stock.today, strike, mark, breakeven, type));
    }

    function closeOptionModal() {
      const modal = document.getElementById('option-modal');
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }

    function drawPayoffDiagram(spot, strike, premium, breakeven, type) {
      const canvas = document.getElementById('payoff-canvas');
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.parentElement.clientWidth;
      const h = canvas.parentElement.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);

      ctx.fillStyle = '#04102b';
      ctx.fillRect(0, 0, w, h);

      const minS = spot * 0.78;
      const maxS = spot * 1.22;
      const steps = 60;
      const points = [];
      for (let i = 0; i <= steps; i++) {
        const s = minS + (i / steps) * (maxS - minS);
        const intrinsic = type === 'CALL' ? Math.max(0, s - strike) : Math.max(0, strike - s);
        const pnl = (intrinsic - premium) * 100;
        points.push({ s, pnl });
      }

      const maxPnl = Math.max(premium * 250, ...points.map(p => p.pnl));
      const minPnl = -premium * 140;

      const toX = s => 45 + ((s - minS) / (maxS - minS)) * (w - 65);
      const toY = pnl => 15 + (h - 38) - ((pnl - minPnl) / (maxPnl - minPnl)) * (h - 38);
      const zeroY = toY(0);

      // Zero Breakeven Horizontal Line
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.45)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(45, zeroY);
      ctx.lineTo(w - 20, zeroY);
      ctx.stroke();

      // Current Spot Vertical Dashed Line
      const spotX = toX(spot);
      ctx.save();
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = '#facc15';
      ctx.beginPath();
      ctx.moveTo(spotX, 12);
      ctx.lineTo(spotX, h - 22);
      ctx.stroke();
      ctx.restore();

      // Payoff Line
      ctx.lineWidth = 2.5;
      for (let i = 0; i < points.length - 1; i++) {
        const p1 = points[i];
        const p2 = points[i + 1];
        ctx.strokeStyle = p2.pnl >= 0 ? '#22c55e' : '#ef4444';
        ctx.beginPath();
        ctx.moveTo(toX(p1.s), toY(p1.pnl));
        ctx.lineTo(toX(p2.s), toY(p2.pnl));
        ctx.stroke();
      }

      // Labels
      ctx.fillStyle = '#cbd5e1';
      ctx.font = '600 10px "JetBrains Mono", monospace';
      ctx.fillText('$0', 14, zeroY + 3);
      ctx.fillStyle = '#facc15';
      ctx.fillText(`Spot $${spot.toFixed(0)}`, Math.min(w - 75, Math.max(48, spotX - 24)), 12);
      ctx.fillStyle = '#38bdf8';
      ctx.fillText(`BE: $${breakeven.toFixed(2)}`, Math.min(w - 85, Math.max(48, toX(breakeven) - 24)), h - 6);
    }

    // =========================================================================
    // 8. CSV EXPORT, CLOCK & TOAST NOTIFICATIONS
    // =========================================================================
    function exportCurrentCSV() {
      const headers = ['Ticker,Company,TodayPrice,YesterdayPrice,Change,PctChange,MA20,MA50,MA200,PE,YearlyHigh,YearlyLow,RSI14'];
      const rows = stocksData.map(s =>
        `${s.ticker},"${s.name}",${s.today},${s.yesterday},${s.change},${s.pctChange},${s.ma20},${s.ma50},${s.ma200},${s.pe},${s.high52},${s.low52},${s.rsi}`
      );
      const csvContent = 'data:text/csv;charset=utf-8,' + [headers, ...rows].join('\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `CAPITAL_QUANT_v2_${selectedTicker}_MarketData.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast('Market & Analysis CSV exported.');
    }

    let toastTimeout;
    function showToast(msg, isWarn = false) {
      const banner = document.getElementById('toast-banner');
      const icon = document.getElementById('toast-icon');
      const text = document.getElementById('toast-message');
      text.textContent = msg;
      icon.className = `w-2.5 h-2.5 rounded-full ${isWarn ? 'bg-amber-400' : 'bg-emerald-400'}`;
      banner.classList.remove('hidden');
      banner.classList.add('flex');
      clearTimeout(toastTimeout);
      toastTimeout = setTimeout(() => {
        banner.classList.add('hidden');
        banner.classList.remove('flex');
      }, 3200);
    }

    function updateLiveClock() {
      const now = new Date();
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const pad = n => String(n).padStart(2, '0');
      const formatted = `${months[now.getMonth()]} ${now.getDate()}, ${now.getFullYear()} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
      const clockEl = document.getElementById('live-clock');
      if (clockEl) clockEl.textContent = formatted;
    }

    // Handle Responsive Canvas Redraw
    window.addEventListener('resize', () => {
      if (currentPage === 'analysis') drawStockChart();
    });

    // Initialize Application on Window Load
    window.onload = function () {
      renderMarketWatchTable();
      syncCompanyDropdowns();
      updateLiveClock();
      setInterval(updateLiveClock, 1000);
    };
  </script>
</body>
</html>
