# HUMANITY ONE Local Workspace UI

## Delivery

The FastAPI application serves a responsive single-page interface at \`/\` and static assets under \`/static/\`. The interface uses the existing API and does not bypass its authorization boundary. Agent runs invoke one static allowlisted local tool per explicit owner request; no autonomous loop is present.

## Included workflows

- Owner password login and logout using the existing HTTP-only session cookie.
- Knowledge note creation, listing and lexical search.
- Bounded TXT/Markdown document ingestion, source-chunk search, bounded source-cited context preparation, and provider-backed answer generation only when an injected provider exists and the owner explicitly consents for that request.
- Memory proposal review, explicit approval/rejection, approved memory archive/restore and lifecycle event inspection.
- Responsive layouts for desktop and mobile, semantic headings/labels, keyboard focus indicators, live status announcements and reduced-motion handling.

## Session and privacy behavior

The raw CSRF token returned by login is kept only in JavaScript memory. It is not written to localStorage, sessionStorage, cookies, URLs, or logs. Reloading the page clears the in-memory token; the owner signs in again to obtain a fresh CSRF token. The browser sends same-origin requests with credentials and no-store cache behavior.

The HTML, CSS and JavaScript are served by the local application. No remote fonts, CDNs, analytics, telemetry, or third-party scripts are loaded. The UI displays Markdown/document text as textContent and does not render untrusted HTML.

The root page and static assets are exempt from API authentication only so the owner can reach the login screen. They remain behind the ASGI loopback-only peer check. All workspace data endpoints remain authenticated by default.

## Limitations

This is an initial interface, not a complete product UI. It has no account recovery, MFA, multi-user roles, session management UI, offline service worker, advanced editor, pagination controls, or formal WCAG conformance audit. Browser security still depends on the local machine and operator. Do not expose the API or UI to a LAN or public internet.
