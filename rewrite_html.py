import re

with open('pocket_lb/proxy.py', 'r') as f:
    content = f.read()

# Define the old block to replace. We want to replace everything from `<header class="dashboard-hero">`
# to the end of `<div id="tab-dashboard" class="tab-panel" style="display: block;">`

start_marker = '<header class="dashboard-hero">'
end_marker = '<div id="tab-accounts" class="tab-panel" style="display: none;">'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_html = """<header class="dashboard-hero">
          <div>
            <h2>Dashboard</h2>
            <p class="muted">Real-time metrics and account distribution.</p>
          </div>
          <div class="hero-actions">
            <span class="status {status_class}">{status_label}</span>
          </div>
        </header>

        <div id="tab-dashboard" class="tab-panel" style="display: block;">
          <section class="stats">
            <div class="card stat-card">
              <div class="stat-header">
                <span class="stat-title">Active Accounts</span>
                <div class="stat-icon pink-icon">
                  <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle></svg>
                </div>
              </div>
              <div class="stat-value"><b id="stat-accounts">{len(settings.accounts)}</b></div>
            </div>
            <div class="card stat-card">
              <div class="stat-header">
                <span class="stat-title">Requests Proxied</span>
                <div class="stat-icon cyan-icon">
                  <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline></svg>
                </div>
              </div>
              <div class="stat-value"><b id="stat-requests">{_format_int(total_requests)}</b></div>
            </div>
            <div class="card stat-card">
              <div class="stat-header">
                <span class="stat-title">Total Tokens Used</span>
                <div class="stat-icon pink-icon">
                  <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                </div>
              </div>
              <div class="stat-value"><b id="stat-tokens">{_format_int(total_observed)}</b></div>
            </div>
            <div class="card stat-card">
              <div class="stat-header">
                <span class="stat-title">Total Estimated Remaining</span>
                <div class="stat-icon cyan-icon">
                  <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path></svg>
                </div>
              </div>
              <div class="stat-value"><b id="stat-remaining">{_format_optional_int(total_remaining)}</b></div>
            </div>
          </section>

          <section class="dashboard-section" style="margin-top: 24px; padding: 0; background: transparent; border: 0; box-shadow: none;">
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 24px;">
              
              <!-- Total System Quota -->
              <div class="card" style="display: flex; flex-direction: column;">
                <div class="section-title">
                  <h3>System Quota Utilization</h3>
                </div>
                <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 24px 0;">
                  <div style="position: relative; width: 220px; height: 110px; display: flex; justify-content: center; align-items: flex-end; overflow: hidden; margin-bottom: 24px;">
                    <svg viewBox="0 0 100 50" width="220" height="110" style="position: absolute; bottom: 0;">
                      <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="var(--line)" stroke-width="12" stroke-linecap="round" />
                      <path id="quota-donut" d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="var(--accent)" stroke-width="12" stroke-linecap="round"
                            stroke-dasharray="{int(126 * total_usage_percent / 100)} 126" />
                    </svg>
                    <div style="text-align: center; margin-bottom: 12px; z-index: 2;">
                      <div id="quota-percent" style="font-size: 36px; font-weight: 800; color: var(--text); font-family: var(--mono); line-height: 1;">{total_usage_percent}%</div>
                      <div style="font-size: 13px; color: var(--muted); margin-top: 4px;">Utilized</div>
                    </div>
                  </div>
                  
                  <div style="width: 100%; display: flex; flex-direction: column; gap: 12px;">
                    <div style="display: flex; justify-content: space-between; font-size: 13px;">
                      <span style="color: var(--muted);">Total Limit</span>
                      <b style="color: var(--text); font-family: var(--mono);">{_format_optional_int(total_limit) if total_limit else 'Unlimited'}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 13px;">
                      <span style="color: var(--muted);">Tokens Used</span>
                      <b id="quota-observed" style="color: var(--text); font-family: var(--mono);">{_format_int(total_observed)}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 13px;">
                      <span style="color: var(--muted);">Uncounted (Stream/Unknown)</span>
                      <b id="quota-unknown" style="color: var(--text); font-family: var(--mono);">{_format_int(total_unknown)}</b>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Account Distribution List -->
              <div class="card" style="display: flex; flex-direction: column;">
                <div class="section-title">
                  <h3>Account Distribution</h3>
                  <span id="quota-configured" style="font-size: 13px;">{configured_quota_count}/{len(snapshots)} configured</span>
                </div>
                <div class="bar-chart" id="account-bars" style="flex: 1; display: flex; flex-direction: column; gap: 16px; margin-top: 16px; overflow-y: auto; max-height: 280px; padding-right: 8px;">
                  {_account_bars(snapshots)}
                </div>
              </div>
            </div>
          </section>
        </div>

        """
    
    new_content = content[:start_idx] + new_html + content[end_idx:]
    with open('pocket_lb/proxy.py', 'w') as f:
        f.write(new_content)
    print("Replaced successfully")
else:
    print("Could not find markers")
