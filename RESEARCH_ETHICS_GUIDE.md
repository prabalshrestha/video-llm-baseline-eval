# Research Ethics Guide: Twitter Data Collection

## 🎓 For Academic Research & Publication

### The Ethical Question

You're conducting research on video misinformation using Twitter Community Notes data. You need tweet metadata but Twitter's free API is limited to 100 requests/month. Is it ethical to use web scrapers for academic research that will be published?

### ⚠️ Short Answer

**Use the Twitter Academic Research API** - it's free, unlimited (10M/month), officially sanctioned, and specifically designed for academic research. This is the **most ethical and legally sound approach**.

**Only use scrapers as a last resort**, and if you do, follow strict ethical guidelines and be transparent in your methodology.

---

## 🏆 Recommended Approach: Twitter Academic Research API

### Why This is Best

✅ **Officially Sanctioned**: No ToS violation  
✅ **Unlimited**: 10 million tweets/month  
✅ **Ethically Sound**: No legal concerns  
✅ **Peer-Reviewable**: Accepted by journals  
✅ **Reproducible**: Other researchers can use same method  
✅ **Free**: No cost for academic research  
✅ **Full Access**: Complete historical archive  

### How to Apply

1. **Go to**: https://developer.twitter.com/en/products/twitter-api/academic-research

2. **Requirements**:
   - Affiliated with academic institution (.edu email)
   - Master's student, PhD student, or faculty
   - Clear research purpose and methodology
   - Description of how data will be used
   - No commercial use

3. **Application Process**:
   - Fill out detailed form (~30 minutes)
   - Describe your research project
   - Explain why you need academic access
   - Usually approved in 1-2 weeks

4. **What You Get**:
   ```
   - 10,000,000 tweets per month
   - Full-archive search (all tweets since 2006)
   - Complete metadata
   - User information
   - Media attachments info
   - No rate limits (within quota)
   ```

### Sample Application Text

When applying, mention:
```
Research Title: "Video Large Language Models for Detecting Video-Based 
               Misinformation on Social Media"

Purpose: Evaluating Video LLMs' capability to detect misleading video 
         content using Twitter/X Community Notes as ground truth labels.

Methodology: Collecting tweets with Community Notes that have been 
            flagged for misleading video content, downloading associated 
            videos, and evaluating Video LLM performance.

Data Use: Training and evaluation dataset for misinformation detection 
         research. Results will be published in academic venues.

No commercial use. Data will be handled per IRB guidelines.
```

---

## 📊 If You Must Use Scrapers (Last Resort)

### When Scrapers Might Be Justified

- Academic API application was rejected
- Time-sensitive research (can't wait for approval)
- Need data types not available via API
- Retrospective data collection for ongoing research

### Ethical Requirements

If you use scrapers, you **MUST**:

#### 1. **IRB Approval**
```
✓ Submit your data collection method to your university's IRB
✓ Get explicit approval for web scraping methodology
✓ Follow all IRB guidelines for human subjects research
✓ Note: Public tweets may still require IRB review
```

#### 2. **Transparency in Publications**

Be completely transparent in your methodology section:

```markdown
### Data Collection Methodology

We collected tweet metadata using web scraping techniques as the 
Twitter API's free tier was insufficient for our research needs 
(limited to 100 requests/month) and our Academic API application 
was pending approval.

We used the following Python packages: [tweepy-self/snscrape/etc.], 
which access publicly available Twitter data through Twitter's web 
interface. All collected data consisted of publicly visible tweets 
and no private or protected accounts were accessed.

We acknowledge that this method may violate Twitter's Terms of 
Service, though the data collected is publicly available and our 
use is strictly for non-commercial academic research purposes.

Data collection was approved by [Your University] IRB under 
protocol #[number].
```

#### 3. **Ethical Data Handling**

```
✓ Collect only publicly available data
✓ Don't access private/protected accounts
✓ Respect user privacy in publication
✓ Anonymize user data where possible
✓ Don't share raw scraped data (only aggregated results)
✓ Delete data after research is complete
✓ Follow GDPR/privacy regulations if applicable
```

#### 4. **Minimize Impact**

```
✓ Rate limit your requests (don't hammer servers)
✓ Use caching to avoid repeated requests
✓ Collect only necessary data
✓ Run during off-peak hours if possible
✓ Stop if you receive cease & desist
```

#### 5. **Alternative Data Citation**

```
Consider citing Community Notes dataset itself, which is 
officially provided by Twitter:

"We obtained tweet IDs from the publicly available Twitter 
Community Notes dataset (https://communitynotes.twitter.com/guide/
en/under-the-hood/download-data), which is provided by Twitter/X 
for research purposes. We then collected tweet metadata using..."
```

---

## 📚 Academic Precedents

### Published Research Using Scraped Twitter Data

Many peer-reviewed papers use scraped Twitter data:

1. **Social Science Research**: COVID-19 misinformation studies
2. **Computational Social Science**: Political polarization research  
3. **NLP/ML Research**: Hate speech detection, sentiment analysis
4. **Crisis Informatics**: Disaster response, emergency communication

### How They Handle It

**Common approaches in published papers**:

✅ Transparent disclosure of scraping methods  
✅ Ethical justification (public interest research)  
✅ IRB approval mentioned  
✅ Data sharing restrictions noted  
✅ Privacy protections described  

**Example citations**:
- Many papers in ACL, ICWSM, WWW conferences use scraped data
- Often cite research fair use or public interest exceptions
- Usually note ToS concerns but argue for research exception

---

## 🎯 Recommendation for Your Project

### Your Specific Context

**Project**: Video LLM evaluation for misinformation detection  
**Data Source**: Twitter Community Notes (officially provided)  
**Need**: Tweet metadata (author, engagement, context)  
**Challenge**: API rate limits

### Recommended Approach (Priority Order)

#### Option 1: Twitter Academic Research API ⭐⭐⭐
```
Priority: HIGHEST
Timeline: 1-2 weeks for approval
Cost: Free
Ethics: No concerns
Legality: Fully compliant
```

**Action**: Apply immediately at developer.twitter.com

#### Option 2: Use Community Notes Dataset Fields
```
Priority: HIGH
Timeline: Immediate
Cost: Free
Ethics: No concerns
Legality: Fully compliant
```

The Community Notes dataset already includes some tweet metadata. Check if it has what you need:

```python
# Check what's available in Community Notes data
import pandas as pd
notes = pd.read_csv('data/raw/notes-00000.tsv', sep='\t')
print(notes.columns)

# May already include: tweetId, language, timestamps, etc.
```

#### Option 3: Limited API + Scraper Hybrid
```
Priority: MEDIUM
Timeline: Immediate
Cost: Free
Ethics: Minor concerns
Legality: Scraping violates ToS
```

Use your 100 API calls/month for the most important tweets, then scraper for others:

```python
# Use API for high-priority tweets
important_tweets = api.fetch_tweets(priority_tweet_ids[:100])

# Use scraper only if necessary for remaining tweets
if academic_api_pending:
    remaining_tweets = scraper.fetch_tweets(remaining_ids)
```

#### Option 4: Scraping with Full Disclosure
```
Priority: LOW (last resort)
Timeline: Immediate
Cost: Free
Ethics: Requires careful handling
Legality: ToS violation (research exception argument)
```

Only if Academic API is not available and other options insufficient.

**Requirements**:
- IRB approval
- Full transparency in paper
- Minimal data collection
- Strong research justification

---

## 📝 Sample Methods Section for Paper

### If Using Academic API (Recommended)

```
Data Collection

We collected tweet metadata using the Twitter Academic Research API, 
which provides access to the full Twitter archive for academic research 
purposes. Tweet IDs were obtained from the publicly available Community 
Notes dataset (https://twitter.com/i/communitynotes/download). We 
retrieved full tweet metadata including text, author information, 
engagement metrics, and media attachments for tweets flagged by 
Community Notes as containing potentially misleading video content.

All data collection complied with Twitter's Terms of Service and 
Developer Agreement. This research was approved by Boise State University 
IRB under protocol #[XXX-XXX].
```

### If Using Scrapers (Less Ideal)

```
Data Collection

Tweet IDs were obtained from the publicly available Twitter Community 
Notes dataset, which is officially provided by Twitter/X for transparency 
and research purposes. To retrieve complete tweet metadata, we employed 
web scraping techniques using Python libraries (tweepy-self, snscrape) 
that access publicly visible tweet information.

We acknowledge that web scraping may be inconsistent with Twitter's 
Terms of Service. However, our data collection meets several criteria 
that may justify this approach for academic research:

1. All collected data is publicly available and visible to any internet 
   user without authentication
2. The research serves a clear public interest (understanding 
   misinformation detection)
3. Data is used solely for non-commercial academic research
4. We implement privacy protections and do not republish raw user data
5. Community Notes data itself is officially provided by Twitter for 
   research purposes

This research was approved by Boise State University IRB under protocol 
#[XXX-XXX]. We followed ethical guidelines for web scraping including 
rate limiting, minimal data collection, and appropriate privacy safeguards.

Limitations: Future researchers may not be able to replicate exact data 
collection due to evolving platform policies and technical changes.
```

---

## 🏛️ Legal & Ethical Framework

### Legal Considerations

**Terms of Service**:
- Scraping violates Twitter ToS (Section 4)
- Could theoretically face legal action
- In practice, rarely enforced for academic research

**Computer Fraud and Abuse Act (CFAA)**:
- US law that prohibits unauthorized access
- Academic scraping rarely prosecuted
- Some legal scholars argue research exception

**Copyright**:
- Individual tweets may be copyrighted
- Fair use likely applies for research
- Don't republish full tweet text

### Ethical Framework

**Belmont Report Principles** (Research Ethics):

1. **Respect for Persons**: 
   - Public tweets = implicit consent?
   - Some argue yes for research purposes
   - Consider anonymization

2. **Beneficence**: 
   - Research benefits (misinformation detection) > minimal risks
   - No harm to individuals from metadata collection

3. **Justice**: 
   - Fair distribution of research benefits
   - No exploitation of vulnerable populations

### IRB Considerations

**Does your research need IRB approval?**

✓ **Likely YES if**:
- Analyzing user behavior
- Could identify individuals
- Sensitive topics

✓ **Possibly NO if**:
- Only analyzing platform-level trends
- Complete anonymization
- Aggregate statistics only

**Check with your IRB** - requirements vary by institution.

---

## ✅ Action Plan for Your Research

### Immediate Steps

1. **Apply for Twitter Academic Research API** (Today!)
   - Go to: https://developer.twitter.com/en/apply/academic-research
   - Takes 30-60 minutes to complete
   - Approval typically in 1-2 weeks

2. **Check Existing Data** (This Week)
   - Review Community Notes dataset fields
   - See if it has sufficient metadata
   - May not need additional tweet data

3. **Consult Your Advisor** (This Week)
   - Discuss ethical approach
   - Get guidance on methodology
   - Plan for IRB submission

4. **Submit IRB Protocol** (Next 2 Weeks)
   - Whether using API or scraper, get IRB approval
   - Include data collection methods
   - Detail privacy protections

### While Waiting for Academic API

**Option A: Use What You Have**
```python
# Work with Community Notes data only
# May have enough info for initial analysis
# Can add more detailed metadata later
```

**Option B: Strategic API Use**
```python
# Use your 100/month quota strategically
# Collect metadata for most important tweets
# Focus on quality over quantity for pilot study
```

**Option C: Scrape with Caution**
```python
# Only if necessary for time-sensitive work
# Prepare for full disclosure in paper
# Get IRB approval first
# Plan to replicate with Academic API later
```

---

## 🎯 Bottom Line

### For Your Research Paper

**Ethical Hierarchy** (Best to Worst):

1. ⭐⭐⭐ **Twitter Academic Research API** - Fully ethical, legal, reproducible
2. ⭐⭐⭐ **Community Notes data only** - No additional collection needed
3. ⭐⭐ **Official API (100/month)** - Limited but compliant
4. ⭐ **Scraping with full disclosure + IRB** - Questionable but defensible
5. ❌ **Scraping without disclosure** - Not acceptable for publication

### Recommendation

**Do not use scrapers for your published research** unless:
- You've applied for Academic API and been rejected, AND
- You have IRB approval, AND  
- You'll be fully transparent in your paper, AND
- Your advisor/committee approves, AND
- You have a strong public interest justification

**Instead**:
1. Apply for Academic Research API today (1-2 week wait)
2. Use Community Notes data fields in the meantime
3. Be patient - the ethical approach is worth the wait
4. Your research will be stronger, more reproducible, and ethically sound

---

## 📞 Resources

### Twitter Academic API
- Application: https://developer.twitter.com/en/products/twitter-api/academic-research
- Docs: https://developer.twitter.com/en/docs/twitter-api/academic-research
- FAQ: https://developer.twitter.com/en/docs/twitter-api/faq

### Research Ethics
- Your IRB: [Contact Boise State IRB]
- Belmont Report: https://www.hhs.gov/ohrp/regulations-and-policy/belmont-report/
- APA Ethics Code: https://www.apa.org/ethics/code

### Legal Information
- Twitter ToS: https://twitter.com/en/tos
- CFAA Information: https://www.justice.gov/criminal-ccips/prosecuting-computer-crimes
- Fair Use: https://www.copyright.gov/fair-use/

### Academic Examples
- Look for papers in:
  - ICWSM (International Conference on Web and Social Media)
  - ACL (Association for Computational Linguistics)
  - CHI (Computer-Human Interaction)
  - Social Media + Society journal

Many published papers deal with similar ethical considerations.

---

## 💡 Final Thoughts

**The gold standard for ethical research is transparency and official channels.**

Your research on video misinformation detection is valuable and serves the public interest. Don't compromise it with questionable data collection methods when legitimate options exist.

The Twitter Academic Research API exists specifically for researchers like you. Use it.

If reviewers ask about your data collection during peer review, you want to be able to say: *"We used Twitter's official Academic Research API in compliance with their Terms of Service and our institutional IRB requirements."*

Not: *"We scraped data in violation of Twitter's ToS but believe it's justified for research purposes."*

The extra 1-2 weeks to get proper API access is worth it for:
- Peace of mind
- Ethical soundness
- Legal protection
- Peer acceptance
- Reproducibility
- Your academic reputation

**Good luck with your research!** 🎓
