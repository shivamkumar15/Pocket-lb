import re

with open("pocket_lb/proxy.py", "r") as f:
    content = f.read()

# Replace variables
new_css_vars = """    :root {
      color-scheme: light;
      --bg: #f9fafb;
      --bg-rail: #f3f4f6;
      --panel: #ffffff;
      --panel-raised: #ffffff;
      --line: #e5e7eb;
      --line-strong: #d1d5db;
      --text: #111827;
      --muted: #6b7280;
      --quiet: #9ca3af;
      --accent: #2563eb;
      --accent-ink: #ffffff;
      --warn: #ea580c;
      --danger: #dc2626;
      --success: #16a34a;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    :root[data-theme="dark"] {
      color-scheme: dark;
      --bg: #111827;
      --bg-rail: #1f2937;
      --panel: #111827;
      --panel-raised: #1f2937;
      --line: #374151;
      --line-strong: #4b5563;
      --text: #f9fafb;
      --muted: #9ca3af;
      --quiet: #6b7280;
      --accent: #3b82f6;
      --accent-ink: #ffffff;
      --warn: #f97316;
      --danger: #ef4444;
      --success: #22c55e;
    }
"""
content = re.sub(
    r':root \{.*?--success: #10b981;.*?\}',
    new_css_vars,
    content,
    flags=re.DOTALL
)

# Remove the body background
content = re.sub(
    r'body \{\n\s*background-image: radial-gradient.*?\n\s*background-size: 120px 120px;\n\s*\}',
    'body { background: var(--bg); }',
    content,
    flags=re.DOTALL
)

# Change .stat-card styles
content = re.sub(
    r'\.stat-card \{.*?\n\s*overflow: hidden;\n\s*\}',
    '.stat-card {\n      background: var(--panel);\n      border-radius: 8px;\n      padding: 16px 20px;\n      display: flex;\n      align-items: center;\n      justify-content: space-between;\n      border: 1px solid var(--line);\n      position: relative;\n    }',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'\.stat-card::after \{.*?\}',
    '',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'\.stat-card\.pink-glow::after \{.*?\}',
    '',
    content,
    flags=re.DOTALL
)
content = re.sub(
    r'\.stat-card\.cyan-glow::after \{.*?\}',
    '',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'\.pink-icon \{.*?\}',
    '.pink-icon {\n      background: var(--bg-rail);\n      color: var(--text);\n    }',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'\.cyan-icon \{.*?\}',
    '.cyan-icon {\n      background: var(--bg-rail);\n      color: var(--text);\n    }',
    content,
    flags=re.DOTALL
)

# Card styling
content = re.sub(
    r'\.card, \.dashboard-section.*?box-shadow:.*?;',
    '.card, .dashboard-section, .chart-panel, .mini-chart-panel, .endpoint-panel, .quota-panel, .account-card {\n      background: var(--panel);\n      border: 1px solid var(--line);\n      border-radius: 8px;\n      padding: 24px;',
    content,
    flags=re.DOTALL
)
content = re.sub(
    r'\.account-card:hover \{.*?\}',
    '.account-card:hover { border-color: var(--accent); }',
    content,
    flags=re.DOTALL
)

# SVG fills
content = re.sub(r'#ff00a0', 'var(--text)', content)
content = re.sub(r'#00f0ff', 'var(--muted)', content)
content = re.sub(r'pink-glow', '', content)
content = re.sub(r'cyan-glow', '', content)
content = re.sub(r'filter="drop-shadow.*?"', '', content)
content = re.sub(r'box-shadow: 0 0 12px.*?;', '', content)
content = re.sub(r'text-shadow: 0 0 4px.*?;', '', content)
content = re.sub(r'box-shadow: 0 0 8px.*?;', '', content)
content = re.sub(r'filter: drop-shadow.*?;', '', content)

with open("pocket_lb/proxy.py", "w") as f:
    f.write(content)
