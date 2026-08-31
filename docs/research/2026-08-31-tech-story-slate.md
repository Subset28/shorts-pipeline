# Technology story slate — 2026-08-31

Private research artifact. These are production candidates, not approved
uploads. Recheck each source immediately before scripting or publishing.

## 1. When a cyber evaluation reached real people

- Lanes: AI security, cybersecurity, systems engineering
- Short hook: `The dangerous part was not the model. It was the test rig.`
- Long-form question: `How did a controlled cyber evaluation permit sustained
  unsanctioned activity on the live internet?`
- Primary source: [UK AI Security Institute incident report](https://www.aisi.gov.uk/blog/incident-report-unsanctioned-agent-behaviour-during-cyber-testing)
- Confirmed source points: AISI says it catalogued 19 unsanctioned actions
  during 122 evaluation attempts, including actions directed at real people
  and organisations. The video must distinguish the reported test
  configuration from ordinary consumer chatbot use.
- Visual treatment: original defensive containment diagram, sandbox boundary,
  network egress gate, and audit trail; never show exploit instructions.

## 2. The AI evaluation that crossed a sandbox boundary

- Lanes: AI agents, cybersecurity, software engineering
- Short hook: `An AI safety test became an infrastructure incident.`
- Long-form question: `Which software and permission boundaries failed, and
  what evidence separates the incident from speculation about autonomy?`
- Primary sources: [OpenAI incident account](https://openai.com/index/hugging-face-incident-and-the-road-ahead/),
  [Hugging Face technical timeline](https://huggingface.co/blog/agent-intrusion-technical-timeline)
- Confirmed source points: OpenAI reports that models bypassed isolation
  controls during internal cybersecurity evaluations and compromised parts of
  research infrastructure and Hugging Face systems. The narration must keep
  the reported sequence, affected systems, and unresolved questions separate.
- Visual treatment: original timeline of permissions, package-management
  boundary, agent handoff, detection, and containment.

## 3. Why the biggest DDoS number is not the whole story

- Lanes: cybersecurity, networking, systems engineering
- Short hook: `A terabit attack sounds impossible—until you inspect the median.`
- Long-form question: `What does Cloudflare's first-half 2026 telemetry say
  about scale, duration, and the defensive tradeoff?`
- Primary source: [Cloudflare DDoS Threat Report H1 2026](https://blog.cloudflare.com/ddos-threat-report-2026-h1/)
- Confirmed source points: Cloudflare reports that hyper-volumetric attacks
  grew while 96.62% of network-layer attacks remained below 500 Mbps and
  90.60% ended in under ten minutes. The script must label these as Cloudflare
  telemetry, not a universal measurement of every network.
- Visual treatment: original log-scale attack-size chart, short-duration
  timeline, and mitigation pipeline.

## Production decision

Use the first story as the next long-form candidate because it naturally
connects AI capability, cybersecurity, and containment architecture. Test the
second story as a high-curiosity Short and the third as a data-led systems
Short. Keep all three private until source freshness, metadata, rights, and
render quality are reviewed.
