## 2026-09-01T16:08:52Z
You are Explorer 2 (Deployment & Packaging Specialist) for AirSense-v2.
Working directory: c:\Users\HP\AirSense-v2\.agents\explorer_survey_2
Original request path: c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md

Your Task:
1. Read c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md completely.
2. Investigate static hosting architectures for zero-config 24/7 cloud deployment on Vercel and GitHub Pages:
   - File layout for standalone static site (pure static HTML/CSS/JS or Vite/Vanilla build output).
   - Vercel configuration (vercel.json, headers, clean URLs, CSP/WSS permissions).
   - GitHub Pages setup (GitHub Actions workflow .github/workflows/deploy.yml or root static branch structure).
   - Browser security constraints: mixed content rules (HTTPS site connecting to WSS vs WS), CORS, Content Security Policy (connect-src wss://broker.hivemq.com:8884 ws://broker.hivemq.com:8000 https: http:).
   - Zero-dependency runtime requirements (no Node.js/Python server required at runtime).
3. Document packaging strategy, configuration files needed, and deployment verification steps.
4. Write your findings to c:\Users\HP\AirSense-v2\.agents\explorer_survey_2\analysis.md and c:\Users\HP\AirSense-v2\.agents\explorer_survey_2\handoff.md.
5. Send a concise completion message back with the handoff path.
