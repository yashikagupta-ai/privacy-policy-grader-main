/**
 * app.js — Privacy Policy Grader Main Controller v5
 * Fixes: dark mode toggle, results persistence (loadRecentAnalyses removed from
 * DOMContentLoaded), grade-reveal animation, emoji removal, clearResults button,
 * confirmed_critical cross-signal fusion rendering, download report.
 */

'use strict';

const State = {
  currentData:    null,
  comparisonData: null,
  benchmarksData: null,
};

const $ = id => document.getElementById(id);

const DOM = {
  form:              $('analyze-form'),
  urlInput:          $('url-input'),
  analyzeBtn:        $('analyze-btn'),
  btnText:           document.querySelector('#analyze-btn .btn-text'),
  btnSpinner:        document.querySelector('#analyze-btn .btn-spinner'),
  errorBanner:       $('error-banner'),
  errorMsg:          $('error-message'),
  errorClose:        $('error-close'),
  progressSection:   $('progress-section'),
  progressBar:       $('progress-bar'),
  resultsSection:    $('results-section'),
  compareSection:    $('compare-section'),
  benchmarksSection: $('benchmarks-section'),
  btnCompare:        $('btn-compare-toggle'),
  btnBenchmarks:     $('btn-benchmarks-toggle'),
  compareForm:       $('compare-form'),
  compareResults:    $('compare-results'),
  benchmarksGrid:    $('benchmarks-grid'),
  hintBtns:          document.querySelectorAll('.hint-btn'),
};

let _radarChart  = null;
let _gradeCard   = null;
let _rfRenderer  = null;
let _cmpRenderer = null;

// ── Progress ──────────────────────────────────────────────────────────────────

const STEPS = ['step-scrape','step-preprocess','step-llm','step-grade','step-verify'];
const STEP_LABELS = {
  'step-scrape':     { icon: '—', label: 'Fetching policy page' },
  'step-preprocess': { icon: '—', label: 'Computing NLP metrics' },
  'step-llm':        { icon: '—', label: 'AI comprehension (Gemini)' },
  'step-grade':      { icon: '—', label: 'Calculating grade' },
  'step-verify':     { icon: '—', label: 'Verifying claims' },
};

function setProgress(pct) {
  if (DOM.progressBar) DOM.progressBar.style.width = pct + '%';
}

function stepDone(id) {
  const el = $(id);
  if (!el) return;
  el.classList.remove('active');
  el.classList.add('done');
  const iconEl = el.querySelector('.step-icon');
  if (iconEl) iconEl.innerHTML = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>';
}

function stepActive(id) {
  const el = $(id);
  if (!el) return;
  el.classList.add('active');
  el.classList.remove('done');
}

function resetSteps() {
  STEPS.forEach(id => {
    const el = $(id);
    if (!el) return;
    el.className = 'step';
    const iconEl = el.querySelector('.step-icon');
    const label = STEP_LABELS[id];
    if (iconEl && label) iconEl.textContent = label.icon;
  });
  setProgress(0);
}

let _pasteTimers = [];

function startProgress() {
  resetSteps();
  DOM.progressSection.classList.remove('hidden');
  $('empty-state')?.classList.add('hidden');
  $('skeleton-loader')?.classList.remove('hidden');
  DOM.resultsSection.classList.add('hidden');
  window.scrollTo({ top: DOM.progressSection.offsetTop - 80, behavior: 'smooth' });

  stepActive('step-scrape');
  setProgress(20);

  const stepTimings = [
    ['step-preprocess', 1200, 40],
    ['step-llm',        2800, 65],
    ['step-grade',      6000, 85],
    ['step-verify',     8000, 95],
  ];

  _pasteTimers = stepTimings.map(([id, delay, pct]) =>
    setTimeout(() => { stepDone(id === 'step-preprocess' ? 'step-scrape' : ''); stepActive(id); setProgress(pct); }, delay)
  );
}

function finishProgress() {
  _pasteTimers.forEach(clearTimeout);
  STEPS.forEach(stepDone);
  setProgress(100);
  setTimeout(() => {
    DOM.progressSection.classList.add('hidden');
    $('skeleton-loader')?.classList.add('hidden');
  }, 600);
}

// ── Error ─────────────────────────────────────────────────────────────────────

function showError(msg) {
  let displayMsg = msg;
  if (typeof msg === 'object' && msg !== null) {
    displayMsg = msg.message || JSON.stringify(msg);
  }
  if (DOM.errorMsg) DOM.errorMsg.textContent = displayMsg;
  DOM.errorBanner?.classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function hideError() { DOM.errorBanner?.classList.add('hidden'); }

// ── Loading ───────────────────────────────────────────────────────────────────

function setLoading(loading) {
  if (DOM.analyzeBtn) DOM.analyzeBtn.disabled = loading;
  DOM.btnText?.classList.toggle('hidden', loading);
  DOM.btnSpinner?.classList.toggle('hidden', !loading);
}

// ── Analysis ──────────────────────────────────────────────────────────────────

async function runAnalysis(url) {
  hideError();
  setLoading(true);
  resetSteps();
  DOM.progressSection.classList.remove('hidden');
  $('empty-state')?.classList.add('hidden');
  $('skeleton-loader')?.classList.remove('hidden');
  DOM.resultsSection.classList.add('hidden');
  window.scrollTo({ top: DOM.progressSection.offsetTop - 80, behavior: 'smooth' });

  const stepTimings = [
    ['step-scrape',     0,    20],
    ['step-preprocess', 2000, 42],
    ['step-llm',        3500, 66],
    ['step-grade',      5500, 85],
    ['step-verify',     6800, 95],
  ];

  const timers = stepTimings.map(([id, delay, pct]) =>
    setTimeout(() => { stepActive(id); setProgress(pct); }, delay)
  );

  let result;
  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const json = await resp.json();
    if (!json.success) {
      const errorMsg = (json.error && typeof json.error === 'object') ? json.error.message : json.error;
      throw new Error(errorMsg || 'Analysis failed');
    }
    result = json.data;
  } catch (err) {
    timers.forEach(clearTimeout);
    DOM.progressSection.classList.add('hidden');
    $('skeleton-loader')?.classList.add('hidden');
    setLoading(false);
    showError(err.message || 'Could not complete analysis. Please try again.');
    return;
  }

  timers.forEach(clearTimeout);
  STEPS.forEach(stepDone);
  setProgress(100);

  setTimeout(() => {
    DOM.progressSection.classList.add('hidden');
    $('skeleton-loader')?.classList.add('hidden');
    setLoading(false);
    State.currentData = result;
    renderResults(result);
    loadRecentAnalyses();
  }, 450);
}

// ── Results rendering ─────────────────────────────────────────────────────────

function renderResults(data) {
  DOM.resultsSection.classList.remove('hidden');
  window.scrollTo({ top: DOM.resultsSection.offsetTop - 80, behavior: 'smooth' });

  renderGradeCard(data);
  renderRadar(data);
  renderMetadata(data);
  renderRedFlags(data.red_flags || []);
  renderSummary(data);
  renderUserRights(data.findings?.user_rights || {});
  renderDataCollected(data.findings?.data_collected || []);
  renderDataShared(data.findings?.data_shared || []);
  renderNLPMetrics(data.metrics || {});
  renderCompliance(data.findings?.compliance_indicators || []);
  renderVerification(data.verification || {});
  renderConfirmedCritical(data.findings?.confirmed_critical || []);

  // Show download button
  const dlBtn = $('download-report-btn');
  if (dlBtn) dlBtn.style.display = 'inline-flex';

  // Trigger grade reveal animation after cards appear
  setTimeout(() => {
    const gl = $('grade-letter');
    if (gl) { gl.classList.remove('revealed'); void gl.offsetWidth; gl.classList.add('revealed'); }
  }, 200);

  // Trigger card animations
  setTimeout(() => {
    DOM.resultsSection.classList.add('loaded');
    document.querySelectorAll('#results-section .card').forEach((card, i) => {
      card.style.transitionDelay = `${i * 55}ms`;
      card.classList.add('visible');
    });
    // Animate dim bars after cards appear
    setTimeout(() => {
      document.querySelectorAll('.dim-bar').forEach(bar => {
        const w = bar.dataset.width;
        if (w) bar.style.width = w + '%';
      });
    }, 300);
  }, 100);
}

function renderGradeCard(data) {
  const { grade, overall_score, company_name, dimension_scores, trust_score } = data;

  $('company-name-badge').textContent = company_name || '';
  $('grade-letter').textContent = grade;
  $('grade-letter').className = `grade-letter grade-${grade}`;

  const scoreEl = $('grade-score');
  if (scoreEl) {
    const targetScore = Math.round(overall_score || 0);
    scoreEl.innerHTML = `<span>${targetScore}</span> <small style="font-size:0.7em;opacity:0.6">/ 100</small>`;
  }

  $('grade-label').textContent = gradeLabel(grade);

  if (trust_score !== undefined) {
    const wrap = $('trust-score-wrap');
    if (wrap) {
      wrap.style.display = 'block';
      $('trust-score-value').textContent = `${trust_score.toFixed(1)} / 100`;
      setTimeout(() => {
        const bar = $('trust-score-bar');
        if (bar) bar.style.width = `${trust_score}%`;
      }, 400);
    }
  }

  // Canvas arc
  const canvas = $('grade-canvas');
  if (canvas) {
    _gradeCard = new GradeCard(canvas, grade, overall_score);
    _gradeCard.draw();
  }

  // Dimension bars
  const breakdown = $('dimension-breakdown');
  if (!breakdown) return;
  breakdown.innerHTML = '';

  const dimLabels = {
    data_collection_transparency: 'Data Collection',
    sharing_disclosure:           'Sharing',
    user_rights:                  'User Rights',
    readability:                  'Readability',
    compliance:                   'Compliance',
  };

  Object.entries(dimension_scores || {}).forEach(([k, v]) => {
    const pct  = Math.round(v);
    const grLet = scoreToGrade(pct);
    const label = dimLabels[k] || k.replace(/_/g, ' ');
    const row = document.createElement('div');
    row.className = 'dim-row';
    row.innerHTML = `
      <span class="dim-label">${label}</span>
      <div class="dim-bar-wrap">
        <div class="dim-bar bar-${grLet}" data-width="${pct}" style="width:0%"></div>
      </div>
      <span class="dim-val grade-${grLet}">${pct}</span>`;
    breakdown.appendChild(row);
  });
}

function renderRadar(data) {
  const canvas = $('radar-canvas');
  if (!canvas) return;
  const dims = data.dimension_scores || {};
  const labels = ['Data\nCollection','Sharing','User\nRights','Readability','Compliance'];
  const values = [
    dims.data_collection_transparency || 0,
    dims.sharing_disclosure           || 0,
    dims.user_rights                  || 0,
    dims.readability                  || 0,
    dims.compliance                   || 0,
  ];
  _radarChart = new RadarChart(canvas, labels, values);
  _radarChart.draw();
}

function renderMetadata(data) {
  const { scraped = {}, metrics = {}, dark_pattern_score } = data;
  const grid = $('meta-grid');
  if (!grid) return;

  // Truncate URL for display to avoid overlap
  const urlDisplay = (data.url || '').length > 48
    ? (data.url || '').substring(0, 48) + '…'
    : (data.url || '');

  const items = [
    ['📄 Policy URL',       `<a href="${esc(data.url)}" target="_blank" rel="noopener" title="${esc(data.url)}">${esc(urlDisplay)}</a>`],
    ['🗓 Last Updated',    esc(scraped.last_updated || 'Unknown')],
    ['📝 Word Count',       (metrics.word_count || 0).toLocaleString()],
    ['🎓 Reading Level',   metrics.flesch_kincaid_grade ? `Grade ${metrics.flesch_kincaid_grade}` : '—'],
    ['⚠️ Dark Pattern',    `${(dark_pattern_score||0).toFixed(0)} / 100`],
    ['🔤 Jargon Density',  `${(metrics.jargon_density||0).toFixed(1)}%`],
    ['📑 Sections',        String(scraped.section_count ?? metrics.section_count ?? '—')],
    ['✅ Clause Coverage', `${(metrics.clause_completeness_score||0).toFixed(0)}%`],
  ];

  grid.innerHTML = items.map(([label, val]) =>
    `<div class="meta-item">
      <div class="meta-label">${label}</div>
      <div class="meta-value">${val}</div>
    </div>`
  ).join('');
}

function renderRedFlags(flags) {
  const el    = $('red-flags-list');
  const card  = $('red-flags-card');
  const banner = $('critical-alert-banner');

  if (!flags.length) {
    if (card) card.classList.add('hidden');
    if (banner) banner.innerHTML = '';
    return;
  }

  if (card) card.classList.remove('hidden');

  // Use the renderer class (which handles filtering)
  if (!_rfRenderer) {
    _rfRenderer = new RedFlagsRenderer(el, $('rf-count'), $('rf-filter'));
  }
  _rfRenderer.render(flags);

  // Critical banner
  const criticalCount = flags.filter(f => f.severity === 'critical').length;
  if (banner) {
    if (criticalCount > 0) {
      banner.innerHTML = `<div class="red-flag-banner">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        <span><strong>Action Required:</strong> ${criticalCount} critical privacy issue${criticalCount>1?'s':''} found — review below.</span>
      </div>`;
    } else {
      banner.innerHTML = '';
    }
  }
}

function renderSummary(data) {
  const el = $('policy-summary');
  if (el) el.textContent = data.findings?.summary || 'No summary available.';
}

// Rights display labels
const RIGHTS_LABELS = {
  access:      'A',
  deletion:    'D',
  portability: 'P',
  correction:  'C',
  opt_out:     'O',
  consent:     'Co',
  complaint:   'Cm',
  default:     'R',
};

function renderUserRights(rights) {
  const grid = $('user-rights-grid');
  if (!grid) return;

  const entries = Object.entries(rights);
  if (!entries.length) {
    grid.innerHTML = '<p class="prose" style="color:var(--clr-muted)">No user rights information found.</p>';
    return;
  }

  grid.innerHTML = entries.map(([k, v]) => {
    const hasValue = v && String(v).trim().length > 2;
    const displayKey = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const abbr = RIGHTS_LABELS[k] || RIGHTS_LABELS.default;
    const statusClass = hasValue ? 'right-yes' : 'right-no';
    const valueText = hasValue
      ? esc(String(v))
      : '<span style="color:var(--grade-f);font-weight:600">Not mentioned</span>';
    return `<div class="right-item ${statusClass}">
      <div class="right-icon" style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700">${abbr}</div>
      <div class="right-content">
        <div class="right-name">${displayKey}</div>
        <div class="right-value">${valueText}</div>
      </div>
    </div>`;
  }).join('');
}

// Data type sensitivity colours (no emoji)
const DATA_SENS_COLOR = { high: 'var(--clr-danger)', medium: 'var(--clr-accent)', low: 'var(--clr-success)' };

function getDataIcon(_type) { return ''; }

function renderDataCollected(items) {
  const el = $('data-collected-list');
  if (!el) return;
  if (!items.length) {
    el.innerHTML = '<p class="prose" style="color:var(--clr-muted)">No specific data types identified.</p>';
    return;
  }
  el.className = 'data-list';
  el.innerHTML = items.map(d => {
    const sens = d.sensitivity || 'medium';
    const sc = DATA_SENS_COLOR[sens] || DATA_SENS_COLOR.medium;
    return `<div class="data-chip">
      <div class="data-chip-left">
        <div class="data-chip-body">
          <div class="data-chip-label">${esc(d.type || 'Unknown')}</div>
          ${d.purpose ? `<div class="data-chip-detail">${esc(d.purpose)}</div>` : ''}
        </div>
      </div>
      <span class="sensitivity-badge sens-${sens}">${sens}</span>
    </div>`;
  }).join('');
}

function getRecipientIcon(_r) { return ''; }

function renderDataShared(items) {
  const el = $('data-shared-list');
  if (!el) return;
  if (!items.length) {
    el.innerHTML = '<p class="prose" style="color:var(--clr-muted)">No data sharing identified.</p>';
    return;
  }
  el.className = 'data-list';
  el.innerHTML = items.map(d => {
    const icon = getRecipientIcon(d.recipient);
    return `<div class="data-chip">
      <div class="data-chip-left">
        <span class="data-chip-icon">${icon}</span>
        <div class="data-chip-body">
          <div class="data-chip-label">${esc(d.recipient || 'Unknown')}</div>
          ${d.data_type ? `<div class="data-chip-detail">${esc(d.data_type)}</div>` : ''}
        </div>
      </div>
      <span class="${d.opt_out_available ? 'optout-yes' : 'optout-no'}">${d.opt_out_available ? '✓ Opt-out' : '✗ No opt-out'}</span>
    </div>`;
  }).join('');
}

function renderNLPMetrics(metrics) {
  const grid = $('nlp-metrics-grid');
  if (!grid) return;

  const items = [
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>', label: 'Word Count', val: (metrics.word_count||0).toLocaleString() },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>', label: 'Sentences', val: (metrics.sentence_count||0).toLocaleString() },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="9" width="20" height="6" rx="2"/><line x1="6" y1="15" x2="6" y2="12"/><line x1="10" y1="15" x2="10" y2="12"/><line x1="14" y1="15" x2="14" y2="12"/><line x1="18" y1="15" x2="18" y2="12"/></svg>', label: 'Avg Sentence Len', val: metrics.avg_sentence_length ? `${metrics.avg_sentence_length} words` : '—' },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>', label: 'Flesch Ease', val: metrics.flesch_reading_ease != null ? Math.round(metrics.flesch_reading_ease) : '—', sub: '/ 100' },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>', label: 'Reading Grade', val: metrics.flesch_kincaid_grade != null ? `Grade ${metrics.flesch_kincaid_grade}` : '—' },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/></svg>', label: 'Jargon Density', val: metrics.jargon_density != null ? `${metrics.jargon_density.toFixed(1)}%` : '—' },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>', label: 'Passive Voice', val: metrics.passive_voice_percentage != null ? `${Math.round(metrics.passive_voice_percentage)}%` : '—' },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>', label: 'Clause Coverage', val: metrics.clause_completeness_score != null ? `${Math.round(metrics.clause_completeness_score)}%` : '—' },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>', label: '3rd-party Mentions', val: metrics.third_party_mentions ?? '—' },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3v18"/><path d="M14 3v18"/><path d="M10 12h-3a5 5 0 0 1 0-10h11"/></svg>', label: 'Paragraphs', val: metrics.paragraph_count ?? '—' },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>', label: 'GDPR Mentions', val: metrics.gdpr_mentions?.count ?? 0 },
    { icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>', label: 'CCPA Mentions', val: metrics.ccpa_mentions?.count ?? 0 },
  ];

  grid.innerHTML = items.map(({ icon, label, val, sub }) =>
    `<div class="metric-card">
      <span class="metric-icon">${icon}</span>
      <div class="metric-label">${label}</div>
      <div class="metric-value">${val ?? '—'}</div>
      ${sub ? `<div class="metric-sub">${sub}</div>` : ''}
    </div>`
  ).join('');
}

// Compliance tag labels (no emoji)
function getComplianceIcon(text) {
  const t = (text || '').toLowerCase();
  if (t.includes('gdpr'))     return 'GDPR';
  if (t.includes('ccpa'))     return 'CCPA';
  if (t.includes('coppa'))    return 'COPPA';
  if (t.includes('data ret')) return 'Retention';
  if (t.includes('cookie'))   return 'Cookies';
  if (t.includes('opt'))      return 'Opt-out';
  return 'OK';
}

function renderCompliance(indicators) {
  const el = $('compliance-list');
  if (!el) return;
  if (!indicators.length) {
    el.innerHTML = '<p class="prose" style="color:var(--clr-muted)">No compliance indicators detected.</p>';
    return;
  }
  el.className = 'compliance-grid';
  el.innerHTML = indicators.map(c => {
    const tag = getComplianceIcon(c);
    return `<div class="compliance-chip">
      <div class="compliance-chip-icon" style="font-family:var(--font-mono);font-size:0.7rem;font-weight:700">${tag}</div>
      <div class="compliance-chip-text">${esc(c)}</div>
    </div>`;
  }).join('');
}

function renderVerification(v) {
  const card = $('verification-summary')?.closest('.card');

  // Hide if no real data
  if (!v || (!v.total_claims && !v.overall_confidence && !v.summary)) {
    if (card) card.classList.add('hidden');
    return;
  }

  if (card) card.classList.remove('hidden');

  const confidence = typeof v.overall_confidence === 'number'
    ? (v.overall_confidence <= 1 ? v.overall_confidence * 100 : v.overall_confidence)
    : 0;

  const el = $('verification-summary');
  if (!el) return;

  el.innerHTML = `
    <div class="verification-grid">
      <div class="verification-stat">
        <div class="verification-stat-value">${confidence.toFixed(0)}%</div>
        <div class="verification-stat-label">Confidence</div>
      </div>
      <div class="verification-stat">
        <div class="verification-stat-value">${v.total_claims || 0}</div>
        <div class="verification-stat-label">Claims Verified</div>
      </div>
      <div class="verification-stat">
        <div class="verification-stat-value">${v.hallucination_count || 0}</div>
        <div class="verification-stat-label">Potential Hallucinations</div>
      </div>
    </div>
    ${v.summary ? `<p class="verification-summary-text">${esc(v.summary)}</p>` : ''}`;
}

// ── Confirmed Critical rendering ──────────────────────────────────────────────

function renderConfirmedCritical(items) {
  const el = $('confirmed-critical-section');
  if (!el) return;
  if (!items || !items.length) { el.classList.add('hidden'); return; }
  el.classList.remove('hidden');
  el.className = 'confirmed-critical-section';
  el.innerHTML = `
    <div class="confirmed-critical-title">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      Confirmed Critical Findings (${items.length})
      <small style="font-family:var(--font-mono);font-size:0.72rem;color:var(--clr-muted)">Multi-signal fusion</small>
    </div>
    ${items.map(item => `
      <div class="confirmed-critical-item">
        <div style="font-weight:600;margin-bottom:6px">${esc(item.issue)}</div>
        <div style="font-size:0.9rem;color:var(--clr-muted);line-height:1.6">${esc(item.explanation)}</div>
        <div class="confirmed-critical-signals">
          ${(item.signals||[]).map(s => `<span class="signal-badge">${esc(s)}</span>`).join('')}
        </div>
      </div>
    `).join('')}
  `;
}

// ── Benchmarks ────────────────────────────────────────────────────────────────

async function loadBenchmarks() {
  try {
    const resp = await fetch('/api/benchmarks');
    const json = await resp.json();
    if (!json.success) return;
    State.benchmarksData = json.data;
    renderBenchmarks(json.data.benchmarks || []);
  } catch { /* silent */ }
}

function renderBenchmarks(benchmarks) {
  const grid = DOM.benchmarksGrid;
  if (!grid) return;
  if (!benchmarks.length) { grid.innerHTML = '<p class="prose" style="color:var(--clr-muted)">No benchmarks available.</p>'; return; }
  grid.innerHTML = benchmarks.map(b => {
    const scores = b.avg_scores || {};
    const scoreRows = Object.entries(scores).map(([k, v]) =>
      `<div class="bench-score-row"><span>${k.replace(/_/g,' ')}</span><span>${v?.toFixed(0)}</span></div>`
    ).join('');
    return `<div class="bench-card">
      <div class="bench-industry">${esc(b.industry)}</div>
      <div class="bench-grade grade-${b.avg_grade}">${b.avg_grade}</div>
      <div class="bench-scores">${scoreRows}</div>
      <div style="font-size:.72rem;color:var(--clr-muted);margin-top:8px">${b.sample_size} companies</div>
    </div>`;
  }).join('');
}

// ── Compare ───────────────────────────────────────────────────────────────────

async function runComparison(urlA, urlB) {
  DOM.compareResults.classList.add('hidden');
  DOM.compareResults.innerHTML = '<p class="prose">Analysing both policies… this may take a moment.</p>';
  DOM.compareResults.classList.remove('hidden');
  try {
    const resp = await fetch('/api/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls: [urlA, urlB] }),
    });
    const json = await resp.json();
    if (!json.success) {
      const errorMsg = (json.error && typeof json.error === 'object') ? json.error.message : json.error;
      throw new Error(errorMsg || 'Comparison failed');
    }
    if (!_cmpRenderer) _cmpRenderer = new ComparisonRenderer(DOM.compareResults);
    _cmpRenderer.render(json.data);
  } catch (err) {
    DOM.compareResults.innerHTML = `<p style="color:var(--grade-f)">${esc(err.message)}</p>`;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function gradeLabel(g) {
  return { A:'Excellent Privacy', B:'Good Privacy', C:'Adequate Privacy', D:'Poor Privacy', F:'Very Poor Privacy' }[g] || '';
}
function scoreToGrade(s) {
  if (s >= 90) return 'A'; if (s >= 80) return 'B';
  if (s >= 70) return 'C'; if (s >= 60) return 'D'; return 'F';
}

// ── PDF Download ──────────────────────────────────────────────────────────────

async function downloadReport() {
  const data = State.currentData;
  if (!data) return;

  const btn = $('download-report-btn');
  if (btn) {
    btn.textContent = '⏳ Generating PDF…';
    btn.disabled = true;
  }

  try {
    // Try server-side export first (HTML format for print-to-PDF)
    const exportUrl = data.url && !data.url.startsWith('paste://')
      ? `/api/export?url=${encodeURIComponent(data.url)}&format=html`
      : null;

    if (exportUrl) {
      window.open(exportUrl, '_blank');
    } else {
      // Client-side PDF for pasted policies
      generateClientPDF(data);
    }
  } catch (err) {
    showError('Could not generate report: ' + err.message);
  } finally {
    if (btn) {
      btn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Download PDF Report`;
      btn.disabled = false;
    }
  }
}

function generateClientPDF(data) {
  const grade  = data.grade || '?';
  const score  = Math.round(data.overall_score || 0);
  const trust  = (data.trust_score || 0).toFixed(1);
  const company = data.company_name || 'Analysed Policy';
  const dims   = data.dimension_scores || {};
  const flags  = data.red_flags || [];
  const findings = data.findings || {};
  const metrics = data.metrics || {};
  const verification = data.verification || {};

  const gradeColors = { A:'#1E6838', B:'#1048A0', C:'#845800', D:'#A84800', F:'#A82818' };
  const color = gradeColors[grade] || '#4A7A58';

  const dimRows = Object.entries(dims).map(([k, v]) => {
    const pct = Math.round(v);
    return `<tr>
      <td>${k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</td>
      <td style="font-weight:700;color:${color}">${pct}</td>
      <td><div style="background:#E8E2D8;border-radius:4px;height:10px;overflow:hidden"><div style="width:${pct}%;height:100%;background:${color};border-radius:4px"></div></div></td>
    </tr>`;
  }).join('');

  const flagRows = flags.map(f => {
    const sevColors = { critical:'#A82818', high:'#A84800', medium:'#845800', low:'#1E6838' };
    const sc = sevColors[f.severity] || '#666';
    return `<tr>
      <td><span style="background:${sc}20;color:${sc};padding:2px 8px;border-radius:4px;font-size:.8rem;font-weight:700;text-transform:uppercase">${f.severity||'?'}</span></td>
      <td>${f.issue || f.pattern || ''}</td>
      <td style="font-size:.82rem;color:#666">${(f.explanation||'').substring(0,100)}</td>
    </tr>`;
  }).join('');

  const rights = findings.user_rights || {};
  const rightsRows = Object.entries(rights).map(([k,v]) =>
    `<tr><td>${k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</td>
    <td>${v ? `<span style="color:#1E6838">✓ ${String(v).substring(0,80)}</span>` : '<span style="color:#A82818">✗ Not mentioned</span>'}</td></tr>`
  ).join('');

  const metricRows = [
    ['Word Count', (metrics.word_count||0).toLocaleString()],
    ['Flesch Reading Ease', metrics.flesch_reading_ease ?? '—'],
    ['Reading Grade', metrics.flesch_kincaid_grade ? `Grade ${metrics.flesch_kincaid_grade}` : '—'],
    ['Jargon Density', metrics.jargon_density ? `${metrics.jargon_density.toFixed(1)}%` : '—'],
    ['Passive Voice', metrics.passive_voice_percentage ? `${Math.round(metrics.passive_voice_percentage)}%` : '—'],
    ['Clause Coverage', metrics.clause_completeness_score ? `${Math.round(metrics.clause_completeness_score)}%` : '—'],
  ].map(([k,v]) => `<tr><td>${k}</td><td style="font-weight:600">${v}</td></tr>`).join('');

  const confidence = typeof verification.overall_confidence === 'number'
    ? (verification.overall_confidence <= 1 ? verification.overall_confidence * 100 : verification.overall_confidence).toFixed(0)
    : '0';

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Privacy Report — ${company}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:'DM Sans',sans-serif;font-size:14px;color:#232018;background:#F6F3EE;line-height:1.6;}
  .page{max-width:900px;margin:0 auto;padding:40px 48px;background:#fff;}
  h1{font-family:'DM Serif Display',serif;font-size:2.4rem;font-weight:400;color:${color};margin-bottom:8px;}
  h2{font-family:'DM Serif Display',serif;font-size:1.4rem;font-weight:400;margin:32px 0 16px;padding-bottom:8px;border-bottom:2px solid #EDE9E2;color:#232018;}
  .header-row{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:32px;padding-bottom:24px;border-bottom:2px solid #EDE9E2;}
  .grade-circle{width:110px;height:110px;border-radius:50%;background:${color}18;border:3px solid ${color};display:flex;flex-direction:column;align-items:center;justify-content:center;flex-shrink:0;}
  .grade-letter-big{font-family:'DM Serif Display',serif;font-size:3rem;color:${color};line-height:1;}
  .score-small{font-family:'JetBrains Mono',monospace;font-size:.85rem;color:#786F66;}
  .meta-info{flex:1;padding-left:28px;}
  .meta-info p{margin-bottom:6px;font-size:.88rem;color:#786F66;}
  .meta-info strong{color:#232018;}
  .scores-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:8px;}
  .score-card{background:#F6F3EE;border-radius:10px;padding:14px 16px;border:1px solid #D4CEC4;}
  .score-card-val{font-family:'JetBrains Mono',monospace;font-size:1.6rem;font-weight:600;color:#232018;}
  .score-card-label{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#786F66;font-weight:700;margin-top:3px;}
  table{width:100%;border-collapse:collapse;margin-bottom:6px;}
  th{background:#F6F3EE;text-align:left;padding:9px 12px;font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#786F66;}
  td{padding:9px 12px;border-bottom:1px solid #EDE9E2;font-size:.88rem;vertical-align:top;}
  .summary-box{background:#F6F3EE;border-left:4px solid ${color};padding:16px 20px;border-radius:4px;font-size:.92rem;line-height:1.7;margin-bottom:6px;}
  .footer{margin-top:40px;padding-top:20px;border-top:1px solid #EDE9E2;text-align:center;font-size:.75rem;color:#B0A898;}
  .verify-row{display:flex;gap:16px;margin-bottom:8px;}
  .verify-card{flex:1;background:#F6F3EE;border-radius:8px;padding:14px;text-align:center;border:1px solid #D4CEC4;}
  .verify-val{font-family:'JetBrains Mono',monospace;font-size:1.6rem;font-weight:700;color:#232018;}
  .verify-label{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;color:#786F66;font-weight:700;margin-top:4px;}
  @media print{
    body{background:#fff;}
    .page{max-width:100%;padding:20px 28px;}
    h2{margin-top:24px;}
    .no-break{page-break-inside:avoid;}
    button{display:none;}
  }
</style>
</head>
<body>
<div class="page">
  <button onclick="window.print()" style="float:right;padding:8px 18px;background:${color};color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;font-family:'DM Sans',sans-serif;margin-bottom:12px;">⬇ Print / Save as PDF</button>
  <h1>Privacy Policy Report</h1>
  <div class="header-row">
    <div class="grade-circle">
      <div class="grade-letter-big">${grade}</div>
      <div class="score-small">${score}/100</div>
    </div>
    <div class="meta-info">
      <p><strong>${company}</strong></p>
      ${data.url ? `<p>🔗 <a href="${data.url}" style="color:${color}">${data.url.substring(0,70)}</a></p>` : ''}
      <div class="scores-grid" style="margin-top:14px;">
        <div class="score-card">
          <div class="score-card-val">${score}</div>
          <div class="score-card-label">Overall Score</div>
        </div>
        <div class="score-card">
          <div class="score-card-val">${trust}</div>
          <div class="score-card-label">Trust Score</div>
        </div>
      </div>
      <p style="margin-top:6px;font-size:.82rem;color:#786F66">Analysed: ${new Date().toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'})}</p>
    </div>
  </div>

  <h2>Dimension Scores</h2>
  <table class="no-break">
    <tr><th>Dimension</th><th>Score</th><th style="width:50%">Bar</th></tr>
    ${dimRows}
  </table>

  <h2>Summary</h2>
  <div class="summary-box">${findings.summary || 'No summary available.'}</div>

  ${flags.length ? `<h2>Red Flags (${flags.length})</h2>
  <table class="no-break">
    <tr><th>Severity</th><th>Issue</th><th>Details</th></tr>
    ${flagRows}
  </table>` : ''}

  <h2>User Rights</h2>
  <table class="no-break">
    <tr><th>Right</th><th>Status</th></tr>
    ${rightsRows || '<tr><td colspan="2" style="color:#786F66">No rights information found.</td></tr>'}
  </table>

  <h2>NLP Metrics</h2>
  <table class="no-break">
    <tr><th>Metric</th><th>Value</th></tr>
    ${metricRows}
  </table>

  ${verification.total_claims ? `<h2>Claim Verification</h2>
  <div class="verify-row">
    <div class="verify-card"><div class="verify-val">${confidence}%</div><div class="verify-label">Confidence</div></div>
    <div class="verify-card"><div class="verify-val">${verification.total_claims||0}</div><div class="verify-label">Claims Verified</div></div>
    <div class="verify-card"><div class="verify-val">${verification.hallucination_count||0}</div><div class="verify-label">Hallucinations</div></div>
  </div>
  ${verification.summary ? `<p style="font-size:.88rem;color:#786F66;margin-top:10px">${verification.summary}</p>` : ''}` : ''}

  <div class="footer">
    <p>Generated by <strong>Privy</strong> · Custom NLP + Google Gemini · ${new Date().getFullYear()}</p>
  </div>
</div>
</body>
</html>`;

  const blob = new Blob([html], { type: 'text/html' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `privacy-report-${(company||'policy').toLowerCase().replace(/\s+/g,'-')}.html`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// ── Dark mode toggle ─────────────────────────────────────────────────────────

function toggleDarkMode() {
  const isDark = document.body.dataset.theme === 'dark';
  const next = isDark ? 'light' : 'dark';
  document.body.dataset.theme = next;
  localStorage.setItem('ppg-theme', next);
  _updateThemeIcons(next);
}

function _updateThemeIcons(theme) {
  const moon = $('icon-moon');
  const sun  = $('icon-sun');
  if (!moon || !sun) return;
  if (theme === 'dark') {
    moon.style.display = 'none';
    sun.style.display  = 'block';
  } else {
    moon.style.display = 'block';
    sun.style.display  = 'none';
  }
}

// ── Clear results ─────────────────────────────────────────────────────────────

function clearResults() {
  DOM.resultsSection?.classList.add('hidden');
  $('empty-state')?.classList.remove('hidden');
  $('confirmed-critical-section')?.classList.add('hidden');
  $('critical-alert-banner').innerHTML = '';
  State.currentData = null;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Event listeners ───────────────────────────────────────────────────────────

DOM.form?.addEventListener('submit', e => {
  e.preventDefault();
  const url = DOM.urlInput.value.trim();
  if (url) runAnalysis(url);
});

DOM.errorClose?.addEventListener('click', hideError);

DOM.hintBtns?.forEach(btn => {
  btn.addEventListener('click', () => {
    DOM.urlInput.value = btn.dataset.url;
    DOM.urlInput.focus();
    // Auto-trigger
    DOM.form?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
});

DOM.btnBenchmarks?.addEventListener('click', () => {
  DOM.benchmarksSection.classList.toggle('hidden');
  DOM.compareSection.classList.add('hidden');
  if (!State.benchmarksData) loadBenchmarks();
  if (!DOM.benchmarksSection.classList.contains('hidden')) {
    DOM.benchmarksSection.scrollIntoView({ behavior: 'smooth' });
  }
});

DOM.btnCompare?.addEventListener('click', () => {
  DOM.compareSection.classList.toggle('hidden');
  DOM.benchmarksSection.classList.add('hidden');
  if (!DOM.compareSection.classList.contains('hidden')) {
    DOM.compareSection.scrollIntoView({ behavior: 'smooth' });
  }
});

DOM.compareForm?.addEventListener('submit', async e => {
  e.preventDefault();
  const urlA = $('compare-url-a')?.value?.trim();
  const urlB = $('compare-url-b')?.value?.trim();
  if (urlA && urlB) await runComparison(urlA, urlB);
});

// ── Input tab switching ───────────────────────────────────────────────────────

function switchInputTab(mode) {
  const urlForm    = $('analyze-form');
  const pastePanel = $('paste-panel');
  const tabUrl     = $('tab-url');
  const tabText    = $('tab-text');

  if (mode === 'url') {
    urlForm?.classList.remove('hidden');
    pastePanel?.classList.add('hidden');
    tabUrl?.classList.add('active');
    tabText?.classList.remove('active');
  } else {
    urlForm?.classList.add('hidden');
    pastePanel?.classList.remove('hidden');
    tabUrl?.classList.remove('active');
    tabText?.classList.add('active');
  }
}

$('paste-text')?.addEventListener('input', function() {
  const words = this.value.trim() ? this.value.trim().split(/\s+/).length : 0;
  const wc = $('paste-word-count');
  if (wc) {
    wc.textContent = `${words.toLocaleString()} word${words !== 1 ? 's' : ''}`;
    wc.style.color = words < 50 ? 'var(--grade-f)' : words < 200 ? 'var(--grade-c)' : 'var(--grade-a)';
  }
});

async function analyzeText() {
  const textEl    = $('paste-text');
  const companyEl = $('paste-company');
  const sourceEl  = $('paste-source-url');
  const btn       = $('analyze-text-btn');

  const text = (textEl?.value || '').trim();
  if (!text) { showError('Please paste some policy text first.'); return; }
  if (text.split(/\s+/).length < 50) {
    showError('Text is too short — please paste the complete policy (at least 50 words).');
    return;
  }

  if (btn) {
    btn.querySelector('.btn-text').classList.add('hidden');
    btn.querySelector('.btn-spinner').classList.remove('hidden');
    btn.disabled = true;
  }

  hideError();
  startProgress();

  try {
    const body = { text };
    if (companyEl?.value?.trim()) body.company_name = companyEl.value.trim();
    if (sourceEl?.value?.trim())  body.source_url   = sourceEl.value.trim();

    const resp = await fetch('/api/analyze/text', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    });
    const json = await resp.json();
    finishProgress();

    if (json.success) {
      State.currentData = json.data;
      setTimeout(() => { renderResults(json.data); loadRecentAnalyses(); }, 500);
    } else {
      const errorMsg = (json.error && typeof json.error === 'object') ? json.error.message : json.error;
      showError(errorMsg || 'Analysis failed.');
    }
  } catch (err) {
    showError(`Network error: ${err.message}`);
    finishProgress();
  } finally {
    if (btn) {
      btn.querySelector('.btn-text').classList.remove('hidden');
      btn.querySelector('.btn-spinner').classList.add('hidden');
      btn.disabled = false;
    }
  }
}

// ── Recent Analyses ───────────────────────────────────────────────────────────

async function loadRecentAnalyses() {
  if (sessionStorage.getItem('hideRecent') === 'true') return;
  try {
    const resp = await fetch('/api/benchmarks');
    const json = await resp.json();
    if (!json.success) return;

    const recent = json.data?.recent_analyses || [];
    if (recent.length === 0) return;

    let section = $('recent-section');
    if (!section) {
      section = document.createElement('div');
      section.id = 'recent-section';
      section.className = 'recent-section';
      section.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
          <h3 class="section-title" style="margin:0">Recently Analysed</h3>
          <button onclick="clearRecentAnalyses()" class="btn btn-ghost" style="font-size:0.8rem;padding:6px 14px">Clear All</button>
        </div>
        <div class="recent-grid" id="recent-grid"></div>`;
      const footer = document.querySelector('.footer');
      if (footer) footer.parentNode.insertBefore(section, footer);
      else document.body.appendChild(section);
    } else {
      // Update heading area if section exists
      const hd = section.querySelector('div[style]');
      if (!hd) {
        section.innerHTML = `
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
            <h3 class="section-title" style="margin:0">Recently Analysed</h3>
            <button onclick="clearRecentAnalyses()" class="btn btn-ghost" style="font-size:0.8rem;padding:6px 14px">Clear All</button>
          </div>
          <div class="recent-grid" id="recent-grid"></div>`;
      }
    }

    const grid = $('recent-grid');
    if (!grid) return;

    const gradeColors = { A:'#1E6838', B:'#1048A0', C:'#845800', D:'#A84800', F:'#A82818' };

    grid.innerHTML = recent.slice(0, 6).map(r => {
      const gc = gradeColors[r.grade] || '#786F66';
      const date = r.created_at ? new Date(r.created_at).toLocaleDateString() : '';
      return `
        <div class="recent-card" onclick="quickLoadUrl('${esc(r.url)}')">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
            <div class="recent-card-company">${r.company_name || 'Unknown'}</div>
            <span class="recent-card-grade" style="background:${gc}18;color:${gc}">Grade ${r.grade}</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:flex-end;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:1.15rem;font-weight:700;color:${gc}">${Math.round(r.overall_score)}<small style="font-size:0.72rem;color:var(--clr-muted);font-weight:400">/100</small></span>
            <div class="recent-card-date">${date}</div>
          </div>
        </div>`;
    }).join('');
  } catch (_) {}
}

function clearRecentAnalyses() {
  const section = $('recent-section');
  if (section) section.remove();
  // Remember that user cleared it so it doesn't pop back up this session
  sessionStorage.setItem('hideRecent', 'true');
}

function quickLoadUrl(url) {
  if (!url || url.startsWith('paste://')) return;
  const input = $('url-input');
  if (input) { input.value = url; switchInputTab('url'); }
  DOM.form?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
}

// ── Version history ───────────────────────────────────────────────────────────

async function loadHistory(domain) {
  if (!domain) return;
  try {
    const resp = await fetch(`/api/history/${domain}`);
    const json = await resp.json();
    if (!json.success || json.data.count < 2) return;

    let section = $('history-section');
    if (!section) {
      section = document.createElement('div');
      section.id = 'history-section';
      section.className = 'card history-section';
      section.style.marginTop = '16px';
      const results = $('results-section');
      results?.parentNode?.insertBefore(section, results.nextSibling);
    }

    const versions = json.data.versions;
    section.innerHTML = `
      <div class="card-header"><h2>Policy Version History — ${json.data.domain}</h2></div>
      <div class="history-timeline">
        ${versions.map(v => {
          const d = v.delta;
          const dir = d ? d.direction : 'unchanged';
          return `<div class="history-entry ${dir}">
            <strong>v${v.version}</strong> — Grade <strong>${v.grade}</strong>
            · Score ${Math.round(v.overall_score)} · Trust ${Math.round(v.trust_score || 0)}
            <div class="history-delta">${d ? d.summary : 'First recorded version'}</div>
          </div>`;
        }).join('')}
      </div>`;
    section.classList.add('visible');
  } catch (_) {}
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Apply saved theme, default to light
  const savedTheme = localStorage.getItem('ppg-theme');
  const theme = savedTheme || 'light';
  document.body.dataset.theme = theme;
  _updateThemeIcons(theme);

  // Clear inputs and filters that browsers might persist across reloads
  if ($('url-input')) $('url-input').value = '';
  if ($('paste-text')) $('paste-text').value = '';
  if ($('paste-company')) $('paste-company').value = '';
  if ($('paste-source-url')) $('paste-source-url').value = '';
  if ($('rf-filter')) $('rf-filter').value = 'all';

  loadBenchmarks();
  // NOTE: loadRecentAnalyses() NOT called on init — results only show
  // after the current session's analysis to avoid cross-browser persistence.

  // Scroll-based card animations
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.08 });

  const observeCards = () => {
    document.querySelectorAll('.card:not(.visible)').forEach((card, i) => {
      card.style.transitionDelay = `${i * 50}ms`;
      observer.observe(card);
    });
  };
  observeCards();

  const resultsMut = new MutationObserver(observeCards);
  const rc = $('results-section');
  if (rc) resultsMut.observe(rc, { childList: true, subtree: true });
});

// Expose globals for HTML onclick attributes
window.switchInputTab      = switchInputTab;
window.analyzeText         = analyzeText;
window.downloadReport      = downloadReport;
window.quickLoadUrl        = quickLoadUrl;
window.clearRecentAnalyses = clearRecentAnalyses;
window.toggleDarkMode      = toggleDarkMode;
window.clearResults        = clearResults;
