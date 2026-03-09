<h1 align="center">The Exam Harvester — CLI</h1>

<p align="center">
  <img src="https://github.com/buffal0x/buffal0x.github.io/blob/main/img/github-exam-logo.png?raw=true" alt="project-image">
</p>

<p align="center">
The Exam Harvester is a structured academic scraping framework designed to automate authenticated course platforms and transform complex assignment systems into clean, organized, and human-readable study material.
<br><br>
The system logs in securely, navigates course structures, extracts all questions and related content, and automatically organizes everything into logical academic order.
</p>

<hr>

<h2 align="center">⚙️ Installation & Usage</h2>

<h3>📦 Requirements</h3>

<ul>
  <li>Python 3.10+</li>
  <li>Git</li>
  <li>Linux / macOS / WSL (recommended)</li>
  <li>Playwright Chromium browser</li>
  <li>System dependencies for headless browsers</li>
</ul>

<hr>

<h3>🚀 Installation</h3>

<pre><code># Clone repository
git clone https://github.com/buffal0x/exam-harvester.git
cd exam-harvester

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install browser engine
python -m playwright install chromium
</code></pre>

<hr>

<h3>🔐 Configuration</h3>

<p>Target platform configuration is stored in:</p>

<pre><code>config/site.yml</code></pre>

<p>Credentials are provided securely via environment variables:</p>

<pre><code>export SCRAPER_USERNAME="your_username"
export SCRAPER_PASSWORD="your_password"
</code></pre>

<p>
Authenticated sessions are stored locally and reused automatically.
</p>

<hr>

<h3>▶️ Usage Workflow</h3>

<h4>1️⃣ Login and Save Session</h4>

<pre><code>python -m app.main login</code></pre>

<p>
Opens a visible browser, logs into the platform, and stores session state locally.
This step only needs to be performed once per session.
</p>

<h4>2️⃣ Scrape All Assignments</h4>

<pre><code>python -m app.main sync</code></pre>

<p>
The crawler:
</p>

<ul>
  <li>Navigates course structure</li>
  <li>Identifies assignments</li>
  <li>Automatically starts non-restricted assignments when required</li>
  <li>Skips blacklisted exams and deadline-restricted content</li>
  <li>Extracts all questions from each assignment</li>
</ul>

<h4>3️⃣ Build Course Index & Ordered View</h4>

<pre><code>python -m app.main build-index</code></pre>

<p>This step organizes all scraped data into structured course order:</p>

<ul>
  <li>Assignments sorted chronologically</li>
  <li>Status detection (answered / started / not started / blacklisted)</li>
  <li>Human-readable course index</li>
  <li>Ordered filesystem mirror for easy browsing</li>
</ul>

<h4>4️⃣ Export Unanswered Questions</h4>

<pre><code>python -m app.main export-pending</code></pre>

<p>
Creates a structured study file containing only assignments that still require work.
All questions are grouped per assignment and sorted by course order.
</p>

<hr>

<h3>📂 Output Structure</h3>

<h4>Raw Storage</h4>

<ul>
  <li><b>data/raw/</b> — Original HTML snapshots</li>
  <li><b>data/parsed/</b> — Extracted metadata and readable content</li>
  <li><b>data/manifests/</b> — Crawl index and mapping</li>
</ul>

<h4>Course Organization</h4>

<ul>
  <li><b>data/index/course_index.json</b> — Machine-readable course structure</li>
  <li><b>data/index/course_index.md</b> — Human-readable course overview</li>
  <li><b>data/index/pending_questions.md</b> — Study file for unfinished work</li>
</ul>

<h4>Ordered Assignment View</h4>

<ul>
  <li><b>data/ordered/</b> — Chronological mirror of all assignments</li>
  <li>Each folder contains:</li>
  <ul>
    <li>content.md — Clean extracted questions</li>
    <li>metadata.json — Structured assignment data</li>
    <li>raw.html — Original page snapshot</li>
    <li>screenshot.png — Visual reference</li>
    <li>info.json — Assignment status and metadata</li>
  </ul>
</ul>

<hr>

<h3>🧠 Intelligent Features</h3>

<ul>
  <li>Session-aware authenticated crawling</li>
  <li>Automatic detection of assignment states</li>
  <li>Multi-question extraction per assignment</li>
  <li>Blacklist protection for exams and deadlines</li>
  <li>Chronological academic ordering</li>
  <li>Human-friendly mirrored file structure</li>
  <li>Structured exports for focused studying</li>
</ul>

<hr>

<h3>🛡️ Safety Controls</h3>

<ul>
  <li>Blacklist prevents restricted exam interaction</li>
  <li>No automatic submissions</li>
  <li>No modification of assignment answers</li>
  <li>Read-only academic extraction</li>
</ul>

<hr>

<h3 align="center">
  Creator: <a href="https://www.github.com/buffal0x">@Buffal0x</a>
</h3>
