## 2026-09-01T16:14:45Z
You are Explorer Impl 3 (Packaging & Cloud Hosting Specialist) for AirSense-v2.
Working directory: c:\Users\HP\AirSense-v2\.agents\explorer_impl_3
Original request path: c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md
Scope document: c:\Users\HP\AirSense-v2\PROJECT.md

Your Task:
1. Read c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md and c:\Users\HP\AirSense-v2\PROJECT.md.
2. Formulate the exact packaging and cloud hosting setup:
   - Ensure public/ directory has clean standalone static assets (index.html, opensource.html, paho-mqtt.js) with relative links for GitHub Pages subpath compatibility.
   - Configure vercel.json with outputDirectory, cleanUrls, and complete CSP headers (connect-src wss://broker.hivemq.com:8884 ...).
   - Create .github/workflows/deploy.yml for GitHub Actions Pages deployment.
   - Ensure zero runtime server dependencies for 24/7 global hosting.
3. Write your implementation recommendations to c:\Users\HP\AirSense-v2\.agents\explorer_impl_3\analysis.md and c:\Users\HP\AirSense-v2\.agents\explorer_impl_3\handoff.md.
4. Send a concise completion message back with the handoff path.
