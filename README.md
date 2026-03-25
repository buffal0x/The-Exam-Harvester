<h1 align="center">The Exam Harvester — CLI</h1>

<p align="center">
  <img src="https://github.com/buffal0x/buffal0x.github.io/blob/main/img/github-exam-logo.png?raw=true" alt="project-image">
</p>

<p align="center">
  A configuration-driven scraping pipeline for authenticated learning platforms.
</p>

<p align="center">
  Built with Playwright, Crawlee, YAML-based extraction rules, deterministic storage, and clean Markdown / JSON export.
</p>

<hr>

<h2 align="center">⚙️ Current Project Status</h2>

<p>
The project currently supports:
</p>

<ul>
  <li>Playwright-based login with saved authenticated session</li>
  <li>Crawlee-powered traversal of allowed pages</li>
  <li>Config-driven page detection and extraction</li>
  <li>Structured output as raw HTML, metadata JSON, and Markdown</li>
  <li>URL allow / deny filtering</li>
  <li>Blacklist-based skipping of restricted pages</li>
  <li>Per-course data storage and indexing</li>
  <li>CLI dashboard / terminal UI for scraper progress</li>
</ul>

<hr>

<h2 align="center">🧠 How It Works</h2>

<h3>1. Login</h3>

<p>
The scraper uses Playwright to log into the platform and saves session state locally.
</p>

<pre><code>python -m app.main login</code></pre>

<p>
This creates an authenticated browser state file used by later scraping runs.
</p>

<h3>2. Crawl a Course</h3>

<p>
The crawler opens the selected course, follows allowed links, skips denied routes, and extracts matching pages using the configured selectors and page-type definitions.
</p>

<pre><code>python -m app.main sync
python -m app.main sync 3207192
python -m app.main sync https://studier.nti.se/studentcourses/3207192/exams</code></pre>

<h3>3. Build Course Index</h3>

<p>
The scraper can build a course-level ordered index from the stored outputs, making it easier to inspect what has been scraped and in what order.
</p>

<pre><code>python -m app.main build-index
python -m app.main build-index 3207192
python -m app.main build-index https://studier.nti.se/studentcourses/3207192/exams</code></pre>

<h3>4. Export Pending Questions</h3>

<p>
The project can export unfinished / pending questions into a structured Markdown study file.
</p>

<pre><code>python -m app.main export-pending
python -m app.main export-pending 3207192
python -m app.main export-pending https://studier.nti.se/studentcourses/3207192/exams</code></pre>

<hr>

<h2 align="center">📦 Installation</h2>

<pre><code>git clone https://github.com/YOUR_USERNAME/lesson-scraper.git
cd lesson-scraper

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium</code></pre>

<hr>

<h2 align="center">🔐 Environment Variables</h2>

<p>
Before using the scraper, export your credentials:
</p>

<pre><code>export SCRAPER_USERNAME="your_username"
export SCRAPER_PASSWORD="your_password"</code></pre>

<hr>

<h2 align="center">🗂️ Configuration</h2>

<h3><code>config/site.yaml</code></h3>

<p>
Controls:
</p>

<ul>
  <li>base URL</li>
  <li>login URL</li>
  <li>default course ID</li>
  <li>allow / deny URL rules</li>
  <li>blacklist rules</li>
  <li>start-button selectors</li>
  <li>storage layout</li>
</ul>

<h3><code>config/extractors.yaml</code></h3>

<p>
Defines:
</p>

<ul>
  <li>page types</li>
  <li>match selectors</li>
  <li>field extractors</li>
  <li>HTML cleanup rules</li>
  <li>content-to-Markdown conversion targets</li>
</ul>

<hr>

<h2 align="center">📂 Output Structure</h2>

<p>
The scraper stores data in structured folders. In the current course-based setup, output is saved under:
</p>

<pre><code>data/courses/course_&lt;COURSE_ID&gt;/</code></pre>

<p>
Typical structure:
</p>

<pre><code>data/courses/course_3207192/
├── raw/
├── parsed/
├── manifests/
├── index/
└── ordered/</code></pre>

<h3>Raw</h3>
<ul>
  <li><code>raw/&lt;hash&gt;/raw.html</code></li>
  <li><code>raw/&lt;hash&gt;/screenshot.png</code> (if available)</li>
</ul>

<h3>Parsed</h3>
<ul>
  <li><code>parsed/&lt;hash&gt;/metadata.json</code></li>
  <li><code>parsed/&lt;hash&gt;/content.md</code></li>
</ul>

<h3>Manifest</h3>
<ul>
  <li><code>manifests/manifest.json</code></li>
</ul>

<h3>Index</h3>
<ul>
  <li><code>index/course_index.json</code></li>
  <li><code>index/course_index.md</code></li>
  <li><code>index/pending_questions.md</code></li>
</ul>

<h3>Ordered View</h3>
<ul>
  <li><code>ordered/001-.../content.md</code></li>
  <li><code>ordered/001-.../metadata.json</code></li>
  <li><code>ordered/001-.../info.json</code></li>
  <li><code>ordered/001-.../raw.html</code></li>
</ul>

<hr>

<h2 align="center">🧾 Commands</h2>

<h3>Login</h3>
<pre><code>python -m app.main login</code></pre>

<h3>Sync</h3>
<pre><code>python -m app.main sync
python -m app.main sync 3207192
python -m app.main sync https://studier.nti.se/studentcourses/3207192/exams</code></pre>

<h3>Build Index</h3>
<pre><code>python -m app.main build-index
python -m app.main build-index 3207192
python -m app.main build-index https://studier.nti.se/studentcourses/3207192/exams</code></pre>

<h3>Export Pending Questions</h3>
<pre><code>python -m app.main export-pending
python -m app.main export-pending 3207192
python -m app.main export-pending https://studier.nti.se/studentcourses/3207192/exams</code></pre>

<hr>

<h2 align="center">🚦Status Model</h2>

<p>
The scraper distinguishes between normal processing, blocked pages, and actual failures.
</p>

<ul>
  <li><b>Processed</b> — page was handled</li>
  <li><b>Saved</b> — page output was stored successfully</li>
  <li><b>Blocked / Blacklisted</b> — page was intentionally skipped</li>
  <li><b>Errors</b> — actual failures only, such as timeout, selector failure, bad URL, or code/runtime errors</li>
</ul>

<p>
Blacklisted pages are not considered errors.
</p>

<hr>

<h2 align="center">🛡️ Current Safety / Filtering Logic</h2>

<ul>
  <li>Allowed domains and URL patterns restrict traversal</li>
  <li>Denied patterns prevent navigation into unwanted areas</li>
  <li>Blacklisted titles / link texts / page texts stop restricted pages</li>
  <li>Assignments may be started automatically only when allowed by current rules</li>
  <li>The scraper does not submit assignments automatically</li>
</ul>

<hr>

<h2 align="center">🎨 CLI Design</h2>

<p>
The current terminal interface includes:
</p>

<ul>
  <li>ASCII banner</li>
  <li>session information</li>
  <li>stats panel</li>
  <li>progress panel</li>
  <li>event log panel</li>
</ul>

<p>
The design is intended to provide a cleaner operator view while scraping.
</p>

<hr>

<h2 align="center">📌 Notes</h2>

<ul>
  <li>Always keep your session file and credentials private</li>
  <li>Do not commit authentication state to public repositories</li>
  <li>Use <code>.gitignore</code> to exclude runtime data and secrets</li>
  <li>The current architecture is designed so extraction can be extended without rewriting the whole crawler</li>
</ul>

<hr>

<h2 align="center">🧭 Planned Improvements</h2>

<ul>
  <li>Hidden-answer probe for non-invasive answer discovery</li>
  <li>Cleaner blocked vs error tracking in UI and metadata</li>
  <li>More advanced multi-course management</li>
  <li>Optional Flask / Web UI layer</li>
  <li>Dockerized deployment</li>
</ul>

<hr>

<h3 align="center">
  Creator: <a href="https://github.com/buffal0x">@Buffal0x</a>
</h3>
