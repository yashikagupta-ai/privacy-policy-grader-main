/**
 * redFlags.js — Red flags accordion renderer with working filters.
 */

class RedFlagsRenderer {
  constructor(container, countEl, filterEl) {
    this.container = container;
    this.countEl   = countEl;
    this.filterEl  = filterEl;
    this.allFlags  = [];

    if (filterEl) {
      filterEl.addEventListener('change', () => this._applyFilter());
    }
  }

  static SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
  static SEVERITY_ICON  = { critical: '🔴', high: '🟠', medium: '🟡', low: '🟢' };

  render(flags) {
    this.allFlags = [...flags].sort((a, b) =>
      (RedFlagsRenderer.SEVERITY_ORDER[a.severity] ?? 4) -
      (RedFlagsRenderer.SEVERITY_ORDER[b.severity] ?? 4)
    );
    this._updateCount(this.allFlags.length);
    this._applyFilter();
  }

  _applyFilter() {
    const sev = this.filterEl ? this.filterEl.value : 'all';
    const visible = sev === 'all'
      ? this.allFlags
      : this.allFlags.filter(f => f.severity === sev);
    this._updateCount(this.allFlags.length);
    this._renderVisible(visible);
  }

  _updateCount(n) {
    if (this.countEl) this.countEl.textContent = n;
  }

  _renderVisible(flags) {
    if (!this.container) return;
    this.container.innerHTML = '';

    if (!flags.length) {
      this.container.innerHTML = '<p style="color:var(--clr-muted);font-size:.9rem;padding:12px 0">No flags matching the selected filter.</p>';
      return;
    }

    flags.forEach((flag) => {
      const item = document.createElement('div');
      item.className = `rf-item sev-${flag.severity || 'low'}`;

      const icon = RedFlagsRenderer.SEVERITY_ICON[flag.severity] || '⚪';
      const issue = this._esc(flag.issue || flag.pattern || flag.category || 'Unknown issue');
      const explanation = this._esc(flag.explanation || flag.description || flag.examples?.join('; ') || '');

      item.innerHTML = `
        <div class="rf-header">
          <span class="rf-sev-badge sev-${flag.severity || 'low'}">${icon} ${flag.severity || 'low'}</span>
          <span class="rf-issue">${issue}</span>
          <span class="rf-arrow">▾</span>
        </div>
        <div class="rf-body">
          ${flag.quote ? `<div class="rf-quote">"${this._esc(flag.quote)}"</div>` : ''}
          ${explanation ? `<p class="rf-explanation">${explanation}</p>` : ''}
        </div>`;

      item.querySelector('.rf-header').addEventListener('click', () => {
        item.classList.toggle('expanded');
      });

      this.container.appendChild(item);
    });
  }

  _esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

window.RedFlagsRenderer = RedFlagsRenderer;
