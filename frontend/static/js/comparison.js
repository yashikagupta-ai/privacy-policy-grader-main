/**
 * comparison.js — Side-by-side policy comparison renderer.
 */

class ComparisonRenderer {
  constructor(containerEl) {
    this.container = containerEl;
  }

  static DIMENSION_LABELS = {
    data_collection_transparency: 'Data Collection',
    sharing_disclosure:           'Sharing Disclosure',
    user_rights:                  'User Rights',
    readability:                  'Readability',
    compliance:                   'Compliance',
  };

  render(data) {
    const { policy_a, policy_b, winner, score_delta, key_differences } = data;
    this.container.innerHTML = '';
    this.container.classList.remove('hidden');

    const winnerName = winner || '';
    const delta = Math.abs(score_delta || 0).toFixed(1);

    // Winner banner
    const banner = document.createElement('div');
    banner.className = 'winner-banner';
    banner.innerHTML = `🏆 <span class="grade-A">${this._esc(winnerName)}</span> wins by ${delta} points`;
    this.container.appendChild(banner);

    // Side-by-side grid
    const grid = document.createElement('div');
    grid.className = 'compare-grid';
    grid.innerHTML = `
      <div class="compare-col">
        <h3>
          <span>${this._esc(policy_a.company)}</span>
          <span class="company-badge" style="background:var(--clr-bg); border-color:var(--clr-border)">${policy_a.grade}</span>
        </h3>
        <div class="score-big" style="color:${this._gradeColor(policy_a.grade)}">${policy_a.overall_score?.toFixed(1)}</div>
        <div class="compare-dimensions">
          ${this._dimRows(policy_a.dimension_scores, policy_b.dimension_scores)}
        </div>
      </div>

      <div class="compare-vs">VS</div>

      <div class="compare-col">
        <h3>
          <span>${this._esc(policy_b.company)}</span>
          <span class="company-badge" style="background:var(--clr-bg); border-color:var(--clr-border)">${policy_b.grade}</span>
        </h3>
        <div class="score-big" style="color:${this._gradeColor(policy_b.grade)}">${policy_b.overall_score?.toFixed(1)}</div>
        <div class="compare-dimensions">
          ${this._dimRows(policy_b.dimension_scores, policy_a.dimension_scores)}
        </div>
      </div>`;
    this.container.appendChild(grid);

    // Key differences
    if (key_differences && key_differences.length) {
      const diffCard = document.createElement('div');
      diffCard.className = 'diff-card';
      diffCard.innerHTML = `<h4>Key Differences</h4>`;
      
      const list = document.createElement('div');
      list.className = 'data-list';
      
      key_differences.forEach(d => {
        const item = document.createElement('div');
        item.className = 'delta-item';
        const better = d.delta > 0 ? policy_b.company : policy_a.company;
        item.innerHTML = `
          <span class="delta-label">${this._esc(d.dimension)}</span>
          <span>
            <span class="delta-val">${d.score_a?.toFixed(0)}</span> vs 
            <span class="delta-val">${d.score_b?.toFixed(0)}</span>
            <span class="company-badge" style="margin-left:8px; font-size:0.65rem">${this._esc(better)} better</span>
          </span>`;
        list.appendChild(item);
      });
      diffCard.appendChild(list);
      this.container.appendChild(diffCard);
    }
  }

  _dimRows(dims, refDims) {
    return Object.entries(ComparisonRenderer.DIMENSION_LABELS).map(([k, label]) => {
      const val = (dims[k] || 0).toFixed(0);
      const ref = (refDims[k] || 0);
      const delta = (dims[k] || 0) - ref;
      
      let deltaIcon = '';
      let deltaCls = '';
      if (delta > 2) { deltaIcon = '↑'; deltaCls = 'delta-better'; }
      if (delta < -2) { deltaIcon = '↓'; deltaCls = 'delta-worse'; }

      return `
        <div class="delta-item">
          <span class="delta-label">${label}</span>
          <span class="delta-val ${deltaCls}">${val} <small>${deltaIcon}</small></span>
        </div>`;
    }).join('');
  }

  _gradeColor(g) {
    return { A:'#22c55e', B:'#3b82f6', C:'#f59e0b', D:'#f97316', F:'#ef4444' }[g] || '#6366f1';
  }

  _esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
}

window.ComparisonRenderer = ComparisonRenderer;
