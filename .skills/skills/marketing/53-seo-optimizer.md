---
name: seo-optimizer
description: "Optimize on-page SEO elements through keyword research, strategic title tags, meta descriptions, header hierarchy, internal linking architecture, and schema markup implementation for improved search visibility and ranking."
category: marketing
difficulty: intermediate
model_boost: "Fixes weak models failing to balance SEO technical requirements with user-focused copywriting"
---

# SEO Optimizer

## Purpose
This skill guides comprehensive on-page SEO optimization that balances search engine requirements with user experience. It ensures your content is discoverable through strategic keyword placement, proper HTML structure, clear information hierarchy, and semantic markup—while maintaining natural, engaging writing for human readers.

## When to Use
- Optimizing existing web pages, blog posts, or landing pages for search visibility
- Creating new content with SEO fundamentals baked in from the start
- Addressing current SEO issues revealed by audit tools (low rankings, poor click-through rates)
- Targeting specific keywords with commercial or informational intent
- Building internal linking strategies across site sections
- Implementing schema markup for rich snippets and enhanced search results
- **Do NOT use when**: Creating time-sensitive breaking news, optimizing highly transactional pages that require conversion focus over organic reach, working on content behind paywalls or login walls, or optimizing for PPC landing pages (use conversion optimization instead)

## Instructions

### Step 1: Keyword Research & Intent Analysis
Identify 3-5 primary keywords and 5-10 supporting keywords using these criteria:
- **Primary keyword**: 2-3 words, 50-200 monthly searches, commercial/informational intent match
- **LSI keywords**: Semantically related terms (synonyms, variations, long-tail), naturally integrated
- **Intent alignment**: Match keyword to content type—informational keywords need educational content, commercial keywords need benefit-focused copy
- **Competitor analysis**: Search top-ranking pages for your target keyword; analyze their keyword usage, content structure, word count (typically 1,500-3,000 words for competitive queries)
- Document research in a simple table: Keyword | Monthly Search Volume | Intent Type | Difficulty | Target Placement

### Step 2: Strategic Title Tag Optimization
Create a title tag (50-60 characters) that:
- Leads with primary keyword (within first 3-5 words when possible, but naturally)
- Includes a benefit, number, or curiosity element: "13 Ways to [Primary Keyword] That [Benefit]"
- Stays under 60 characters to display fully in search results (avoid truncation)
- Avoids keyword stuffing; aim for 1 primary keyword mention maximum
- Example patterns:
  - "Primary Keyword | Descriptive Modifier [Brand Name]"
  - "How to [Primary Keyword]: Complete Guide for [Audience]"
  - "[Primary Keyword]: [Number] Strategies & [Benefit]"
- Test different formulations: CTR varies 20-40% based on title phrasing

### Step 3: Meta Description Crafting
Develop a meta description (150-160 characters) that:
- Incorporates primary or supporting keyword naturally (once)
- Opens with an action or benefit, not definition
- Includes a specific promise or answer to the keyword query
- Ends with a soft CTA ("Learn more," "Discover," "See our guide")
- Format: [Benefit/Answer] + [Key Detail] + [Why It Matters] + [CTA]
- Example: "Master on-page SEO with our keyword research framework. Learn title tag optimization, schema markup, and internal linking strategies to boost rankings."
- Poor example: "This page is about SEO optimization" (generic, no benefit, no keyword)

### Step 4: Header Hierarchy & Content Structure
Organize content using this hierarchy:
- **H1** (one per page): Main topic, includes primary keyword once, positions as page title
  - Use for brand/unique angle, not keyword stuffing
  - "The Complete Guide to [Primary Keyword]" or "[Primary Keyword] for [Audience Segment]"
- **H2s** (4-8): Major subtopics, include supporting keywords and LSI terms
  - "Why [Primary Keyword] Matters for [Use Case]"
  - "How to [Supporting Keyword]: Step-by-Step"
  - "Common [Primary Keyword] Mistakes to Avoid"
- **H3s** (8-15): Sub-sections under H2s, break down complex ideas
  - Use to explain steps, examples, or nuances
  - Include long-tail variations naturally
- **Keyword density**: Aim for primary keyword in 0.5-1.5% of total words (for 2,000 words = 10-30 mentions); prioritize H1, first 100 words, and H2s
- **Content flow**: Each section should answer a specific user question; structure mirrors search intent

### Step 5: Internal Linking Architecture
Build internal links that:
- **Anchor text strategy**: Use descriptive anchor text (not "click here"), incorporate keywords naturally
  - 40-50% keyword-rich anchors (e.g., "learn our SEO checklist")
  - 40-50% branded/branded+keyword anchors (e.g., "our keyword research framework")
  - 10-20% generic anchors (e.g., "read more," "this guide")
- **Linking pattern**: Link to 2-4 relevant internal pages per content piece
  - Link early (within first 200 words) to establish relevance
  - Link contextually within body copy, not just footer or sidebars
  - Link to cornerstone content (pillar pages) and related topic clusters
- **Orphan content**: Audit pages with zero internal links; add links from topically related pages
- **Link velocity**: Avoid linking to new pages from too many places at once (suggests over-optimization)

### Step 6: Schema Markup Implementation
Add JSON-LD schema to enhance search visibility:
- **Article schema**: For blog posts and news content
  ```json
  {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "Title Tag Here",
    "description": "Meta description here",
    "image": "featured-image-url",
    "author": {
      "@type": "Person",
      "name": "Author Name"
    },
    "datePublished": "2026-03-05"
  }
  ```
- **FAQPage schema**: For Q&A content, directly answers appear in search results
- **BreadcrumbList schema**: For multi-level site navigation, improves SERP appearance
- **Product schema**: For e-commerce pages (price, ratings, availability)
- **LocalBusiness schema**: For location-based services
- **How-To schema**: For step-by-step guides, appears as rich snippet
- **Organization schema**: Site-wide, on homepage (name, logo, contact)
- Test implementation at schema.org/validator or Google Rich Results Test

### Step 7: Technical SEO Fundamentals
Ensure foundational elements:
- **Page speed**: Target <3 second load time; compress images, minimize CSS/JS, enable caching
- **Mobile responsiveness**: Test on mobile; ensure text is readable, CTAs are tap-friendly
- **URL structure**: Keep URLs short, include primary keyword, use hyphens (not underscores)
  - Example: `/seo-optimizer-guide/` (not `/seo_optimizer_guide` or `/page123`)
- **Canonicalization**: Set canonical tags to prevent duplicate content issues
- **SSL/HTTPS**: Required for all pages
- **XML Sitemap**: Include all indexable pages; update when adding new content
- **Robots.txt**: Allow crawling of important pages; block duplicate or low-value pages

## Output Template

**Page Title:**
- Title tag (50-60 chars): [Your optimized title]
- Primary keyword: [Keyword]
- Secondary keywords: [5-10 keywords]

**Meta Description:**
- [Your 150-160 character meta description]

**Header Outline:**
- H1: [Main heading with primary keyword]
  - H2: [Subtopic with supporting keyword]
    - H3: [Sub-section]
  - H2: [Subtopic with LSI term]

**Internal Links:**
- Anchor "keyword research framework" → [internal page URL]
- Anchor "SEO audit tools" → [internal page URL]

**Schema Markup:**
- Article schema: Added (headline, datePublished, author)
- FAQPage schema: Added ([number] Q&A pairs)

**On-Page Keyword Placement:**
| Keyword | H1 | First 100 Words | H2/H3 | Body | Count |
|---------|----|--------------------|-------|------|-------|
| Primary Keyword | ✓ | ✓ | 3 | 8 | 12 (0.6%) |
| Supporting Keyword 1 | | ✓ | 2 | 4 | 6 (0.3%) |

## Quality Gates

1. **Keyword relevance**: Primary keyword appears in title, H1, and first 200 words; LSI keywords distributed naturally (not forced)
2. **Title tag performance**: Under 60 characters, includes benefit/number, keyword in first 5 words, no keyword stuffing
3. **Meta description engagement**: 150-160 characters, includes benefit + keyword + soft CTA, passes CTR test (higher than previous 3 months)
4. **Header structure clarity**: H1 present and unique, 4-8 H2s covering major subtopics, H3s break down complexity, no header hierarchy skips
5. **Internal linking context**: 2-4 relevant links per 2,000 words, anchor text diverse (40% keyword-rich, 40% branded, 20% generic), links appear in context not footer
6. **Content alignment**: Page length matches competitor content (within 20%), content structure mirrors search intent, no fluff or padding
7. **Technical implementation**: Schema markup validates without errors, canonical tag present, page speed <3 seconds, URL includes keyword, mobile-responsive

## Examples

### Good Example: Blog Post on Keyword Research
- **Title tag**: "Keyword Research Framework: Find Hidden Opportunities | [Brand]" (58 chars)
- **Primary keyword**: "keyword research framework" in H1, meta description, first paragraph
- **Meta description**: "Master keyword research with our proven framework. Learn volume analysis, intent matching, and competitor strategies to find overlooked ranking opportunities."
- **H1**: "The Keyword Research Framework: Finding Search Opportunities Your Competitors Miss"
- **H2 examples**: "Why Keyword Research Matters for SEO Success," "How to Analyze Keyword Volume & Difficulty," "Intent-Driven Keyword Selection (4 Types Explained)"
- **Internal links**: "our SEO audit tools" → tools page, "content calendar strategy" → calendar page
- **Schema**: Article schema with author, date, and FAQPage schema for 8 Q&A pairs
- **Result**: Ranks #3 for primary keyword (within 3 months), 15% CTR improvement

### Bad Example: Overstuffed Landing Page
- **Title tag**: "Keyword Research Framework For Keyword Research And SEO Keywords" (67 chars, truncated, repetitive)
- **Primary keyword**: Appears 28 times in 1,800 words (1.5%, excessive)
- **Meta description**: "We do keyword research frameworks for keyword research and keywords." (generic, no benefit, poor grammar)
- **H1**: Missing; starts directly with H2 "Keyword Research"
- **H2s**: Only 2, vague ("Overview," "Details"), no clear user journey
- **Internal links**: Single footer link, no contextual linking
- **Schema**: None
- **Result**: No ranking improvement after 6 months, 2% CTR, high bounce rate

## Common Mistakes

1. **Keyword stuffing over keyword placement**: Jamming primary keyword repeatedly rather than naturally incorporating LSI keywords and supporting terms. Solution: Use keyword clustering tools to find semantic variations; prioritize H1, first 100 words, and H2s, then let body copy flow naturally.

2. **Ignoring search intent mismatch**: Optimizing for a keyword without confirming user intent (are they looking for "how-to" content, product reviews, or definitions?). Search the keyword and analyze top 3 results. If they're reviews and you're writing a guide, reconsider the keyword target. Solution: Match content type to intent—informational keywords need educational depth, commercial keywords need benefit-focused copy with social proof.

3. **Weak meta descriptions**: Writing descriptions that don't answer the user's search query or include no benefit statement. "Learn more" without specifying what benefit is generic. Solution: Open with an answer or benefit, include one keyword naturally, end with a soft CTA.

4. **Orphaned internal content**: Creating pages that exist on your site but receive zero internal links, leaving them undiscovered by both users and search engines. Audit with tools like Screaming Frog to identify zero-link pages. Solution: Systematically link from topically related pages using keyword-rich anchor text.

5. **Mobile-first indexing oversight**: Optimizing desktop content but not testing mobile experience; Google now crawls and ranks mobile versions first. Solution: Test all pages on mobile devices; ensure text is readable without zooming, CTAs are tap-friendly (44px minimum), and page speed is <3 seconds on 4G.

6. **Schema markup errors**: Implementing schema but not validating with Google Rich Results Test or Schema.org Validator, causing markup to be ignored. Solution: Validate every schema implementation; common errors include wrong context URLs, missing required fields, and JSON syntax errors.

## Anti-Patterns

1. **The Keyword Density Trap**: Obsessing over exact keyword density percentages (e.g., "it must be 1.5%") at the expense of readability. Modern algorithms focus on semantic relevance and user satisfaction, not keyword frequency. Write naturally first, verify keyword distribution second. If density is wildly off (0.1% or >3%), adjust.

2. **Title Tag Brand Obsession**: Prioritizing brand name in title tags over keywords and benefits ("CompanyName | Product Line" with no keyword or benefit, sacrificing CTR). Solution: Lead with benefit or keyword, include brand if space allows at the end.

3. **The Duplicate Content Evasion**: Creating multiple versions of similar content to target different keywords, spreading authority across fragmented pages instead of one authoritative resource. Solution: Create one comprehensive, cornerstone piece for a topic cluster; link from satellite pages using specific keywords to sections within the cornerstone.

4. **Ignoring Page Speed for Content Alone**: Focusing entirely on content quality and keyword optimization while neglecting technical speed (slow image compression, unoptimized fonts, render-blocking CSS). A 5-second page loses 25% of users before they read anything. Solution: Set a page speed budget; compress images, minimize CSS/JS, enable lazy loading.

5. **Internal Linking Without Strategy**: Adding internal links randomly or only in footers rather than strategically within body copy to pass authority to target pages. Solution: Map link architecture intentionally—cornerstone pages receive most links, supporting pages link up to cornerstones, related pages link to each other.

6. **The "Thin Content" Illusion**: Writing 800-word posts when top-ranking competitors average 2,500 words for the same keyword, assuming AI-assisted brevity is enough. Search intent often demands depth. Solution: Analyze top 5 results; match word count (within 20%), but ensure every word adds value—no padding.
