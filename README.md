# JobFit — Resume to Job Matcher

A web app that reads your resume, figures out your role and skill level, and matches you against **live** job postings pulled from real job APIs — not a static dataset.

🔗 **Live app:** https://jobresume-fit.streamlit.app/

---

## What it does

1. **Upload your resume** (PDF)
2. The app extracts your skills, detects your likely role(s), and figures out if you're entry-level or experienced
3. You confirm/edit the detected role and skills
4. It searches **live** postings via the Adzuna and Jooble APIs for your role and chosen city
5. Each result shows a match %, missing skills, salary (when disclosed), and a direct apply link

### Verify Exact Match

Job APIs sometimes truncate long descriptions, which can make match scores less reliable for some postings. This app is upfront about that — every truncated result is flagged, and there's a dedicated section where you can paste a job's full description to get an exact, verified score instead of an estimate.

---

## Supported roles & cities

**Roles:** Data Analyst, Data Scientist, Data Engineer, Software Developer, Web Developer, UI/UX Designer, QA/Testing, DevOps, Mobile App Developer

**Cities:** Ahmedabad, Surat, Mumbai, Bangalore, Delhi, Pune, Hyderabad

This is intentionally scoped — the goal was to build something narrow that works reliably rather than something broad that doesn't.

---

## Tech stack

- **Python** — pdfplumber (PDF parsing), regex-based skill extraction
- **Streamlit** — UI and deployment
- **Adzuna API + Jooble API** — live job data
- **SQLite** — local caching to respect API rate limits
- **Git / GitHub** — version control
- **Streamlit Community Cloud** — hosting

---

## How it works (pipeline)

Resume PDF
   → Text extraction
   → Section splitting (skills, experience, projects, etc.)
   → Skill extraction (regex, role-specific skill lists)
   → Role scoring & selection
   → Entry-level vs experienced detection
   → Live API search (Adzuna + Jooble), cached for 2 hours
   → Merge & dedupe results
   → Match % calculation per posting
   → Display, sorted by match %

---

## Known limitations

- Job descriptions from the free API tier are sometimes truncated (~500 characters), which can inflate or distort match scores — flagged in the UI, and solvable via the Verify Exact Match feature
- Limited to 9 role families and 7 Indian cities for now
- Runs on free-tier APIs with limited daily call quotas

---

## Run it locally

```bash
git clone [your repo link]
cd resume-job-matcher
pip install -r requirements.txt
```

Add your own API keys to `.streamlit/secrets.toml`:
```toml
ADZUNA_APP_ID = "your_app_id"
ADZUNA_APP_KEY = "your_app_key"
JOOBLE_KEY = "your_jooble_key"
```

Then run:
```bash
streamlit run app.py
```

---

## Built by

Yukti Patel — B.E. Information Technology graduate

LinkedIn - https://www.linkedin.com/in/yuktipatel0472/
