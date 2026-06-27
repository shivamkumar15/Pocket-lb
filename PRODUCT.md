# Product

## Register

product

## Users

Developers running OpenCode against Cloudflare Workers AI through a local load-balancing proxy. They are usually configuring accounts, checking whether traffic is flowing, and watching account usage while debugging local model requests.

## Product Purpose

Pocket-lb provides a local OpenAI-compatible endpoint that rotates requests across multiple Cloudflare accounts, retries failed or rate-limited accounts, and keeps Cloudflare credentials on the local machine. Success means a developer can confidently configure accounts, point OpenCode at one URL, and understand account health and observed quota usage without reading logs.

## Brand Personality

Operational, compact, trustworthy. The interface should feel like a focused developer control panel rather than a marketing site.

## Anti-references

Avoid generic SaaS landing-page styling, oversized hero sections, decorative gradients used as content, and dashboards that hide operational details behind vague summary cards.

## Design Principles

Keep the primary endpoint and configuration state visible at all times. Show exact operational data before decorative summaries. Make setup and diagnostics one click away. Preserve local-first security language around secrets. Favor dense but readable developer-tool patterns.

## Accessibility & Inclusion

Use high-contrast dark surfaces, visible focus states, semantic HTML, responsive layouts, and reduced-motion-safe interactions. Do not rely on color alone for quota or health state.
