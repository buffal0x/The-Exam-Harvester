<h1 align="center">The Exam Harvester — CLI</h1>

<p align="center">
  <img src="https://github.com/buffal0x/buffal0x.github.io/blob/main/img/github-exam-logo.png?raw=true" alt="project-image">
</p>

<p align="center">
A structured academic scraping framework for authenticated course platforms.
</p>

<p align="center">
Automates navigation, extracts assignments, and organizes everything into clean, structured study material.
</p>

<hr>

<h2 align="center">⚙️ Current Project Status</h2>

<ul>
  <li>Playwright-based login with persistent session</li>
  <li>Crawlee-powered browser crawling</li>
  <li>Config-driven scraping via YAML</li>
  <li>Automatic assignment detection and extraction</li>
  <li>Blacklist system (prevents exams, deadlines, etc.)</li>
  <li>Auto-start of assignments (non-invasive)</li>
  <li>Structured output (HTML, JSON, Markdown)</li>
  <li>Course-based storage system</li>
  <li>Ordered dataset generation</li>
  <li>CLI dashboard with progress UI</li>
</ul>

<hr>

<h2 align="center">📦 Installation</h2>

<pre><code>git clone https://github.com/YOUR_USERNAME/The-Exam-Harvester.git
cd The-Exam-Harvester

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium</code></pre>

<hr>

<h2 align="center">🔐 Environment Variables</h2>

<pre><code>export SCRAPER_USERNAME="your_username"
export SCRAPER_PASSWORD="your_password"</code></pre>

<hr>

<h2 align="center">📌 Course ID</h2>

<p>
Each course has a unique identifier (<code>COURSE_ID</code>) in the URL:
</p>

<pre><code>https://studier.nti.se/studentcourses/&lt;COURSE_ID&gt;/exams</code></pre>

<p>
Example:
</p>

<pre><code>https://studier.nti.se/studentcourses/1234567/exams</code></pre>

<hr>

<h2 align="center">▶️ Usage</h2>

<h3>Login</h3>

<pre><code>python -m app.main login</code></pre>

<p>
Stores authenticated session for reuse.
</p>

---

<h3>Scrape Course</h3>

<pre><code>python -m app.main sync
python -m app.main sync &lt;COURSE_ID&gt;
python -m app.main sync https://studier.nti.se/studentcourses/&lt;COURSE_ID&gt;/exams</code></pre>

---

<h3>Build Course Index</h3>

<pre><code>python -m app.main build-index
python -m app.main build-index &lt;COURSE_ID&gt;
python -m app.main build-index https://studier.nti.se/studentcourses/&lt;COURSE_ID&gt;/exams</code></pre>

---

<h3>Export Pending Questions</h3>

<pre><code>python -m app.main export-pending
python -m app.main export-pending &lt;COURSE_ID&gt;
python -m app.main export-pending https://studier.nti.se/studentcourses/&lt;COURSE_ID&gt;/exams</code></pre>

<hr>

<h2 align="center">📂 Output Structure</h2>

<pre><code>data/courses/course_&lt;COURSE_ID&gt;/

├── raw/
├── parsed/
├── manifests/
├── index/
└── ordered/
</code></pre>

<h3>Raw</h3>
<ul>
  <li>Full HTML snapshots</li>
  <li>Screenshots (optional)</li>
</ul>

<h3>Parsed</h3>
<ul>
  <li><code>content.md</code> — Clean questions</li>
  <li><code>metadata.json</code> — Structured data</li>
</ul>

<h3>Manifest</h3>
<ul>
  <li>Full crawl metadata</li>
</ul>

<h3>Index</h3>
<ul>
  <li>Course overview</li>
  <li>Status tracking</li>
  <li>Pending questions export</li>
</ul>

<h3>Ordered</h3>
<ul>
  <li>Chronological assignment structure</li>
</ul>

<hr>

<h2 align="center">🚦 Status System</h2>

<ul>
  <li><b>Processed</b> — Page handled</li>
  <li><b>Saved</b> — Successfully stored</li>
  <li><b>Blacklisted</b> — Intentionally skipped</li>
  <li><b>Errors</b> — Actual failures only</li>
</ul>

<hr>

<h2 align="center">🛡️ Safety & Logic</h2>

<ul>
  <li>Strict domain filtering</li>
  <li>Allow / deny URL control</li>
  <li>Blacklist for exams, deadlines, restricted content</li>
  <li>Assignments are only started when safe</li>
  <li>Never submits answers automatically</li>
</ul>

<hr>

<h2 align="center">🎨 CLI Interface</h2>

<ul>
  <li>ASCII banner</li>
  <li>Session info panel</li>
  <li>Live progress bar</li>
  <li>Stats tracking</li>
  <li>Event log with warnings/errors</li>
</ul>

<hr>

<h2 align="center">📌 Notes</h2>

<ul>
  <li>Never commit credentials or session files</li>
  <li>Use <code>.gitignore</code> properly</li>
  <li>Designed for extensibility via YAML config</li>
</ul>

<hr>

<h2 align="center">🧭 Roadmap</h2>

<ul>
  <li>Hidden answer detection (non-invasive)</li>
  <li>Improved CLI UI stability</li>
  <li>Multi-platform support</li>
  <li>Web UI (Flask)</li>
  <li>Docker deployment</li>
</ul>

<hr>

<h3 align="center">
  Creator: <a href="https://github.com/buffal0x">@Buffal0x</a>
</h3>
