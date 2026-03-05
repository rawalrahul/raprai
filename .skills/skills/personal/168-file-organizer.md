---
name: file-organizer
description: "Intelligently organize files and folders by analyzing content, finding duplicates, renaming consistently, and suggesting optimal folder structures"
category: personal
difficulty: beginner
model_boost: "Weak models suggest generic organization without understanding actual content; miss duplicates; create structures that don't match user workflows"
---

# File Organizer: Intelligent Structure & Deduplication System

## Purpose
Transform chaotic file systems into organized, discoverable structures. This skill teaches you to analyze folder contents (sizes, types, ages), detect duplicates using cryptographic hashing, choose appropriate organization strategies, implement consistent naming conventions (YYYY-MM-DD-description), archive cold storage, and build reusable folder templates. Use this to spend 5 minutes finding files instead of 30, reduce storage waste by 20-30%, and maintain structure without effort.

## When to Use / Do NOT use when
**USE WHEN:** Starting new projects, experiencing "lost file" frustration, running low on storage, or inheriting disorganized folders.
**DO NOT:** Use without backing up originals first; avoid organizing files you're actively developing (wait until projects complete).

## Instructions

### Step 1: Scan Folder Tree for Content Analysis
**Gather Metadata** (don't open files, just analyze structure):

```bash
# Folder structure with sizes
du -sh * | sort -rh | head -20
# Shows: Largest folders first (find space hogs)

# File type breakdown
find . -type f -printf "%f\n" | sed 's/.*\.//' | grep -v '^\.' | \
  sort | uniq -c | sort -rn | head -20
# Shows: Document count by extension (PDF, DOCX, IMG, etc)

# Files by age
find . -type f -mtime +365 -ls | wc -l
# Shows: How many files haven't changed in 1+ year (archive candidates)

# Detailed inventory
find . -type f -printf "%T+ %s %p\n" | sort -k1 -r | head -100
# Shows: File, size, date (to spot patterns)

# Duplicate candidates (files over 10MB, probably duplicates if same size)
find . -type f -size +10M -printf "%s %p\n" | sort -k1 -rn | awk '{print $1}' | \
  uniq -d
# Shows: Duplicate file sizes
```

**Record Inventory**:
```
Folder: ~/Documents
Total Size: 45 GB
File Count: 3,200

Size Breakdown:
- Videos: 32 GB (71%)
- Documents: 10 GB (22%)
- Images: 2.5 GB (6%)
- Audio: 500 MB (1%)

Age Breakdown:
- Modified in past 3 months: 40% (active)
- 3-12 months old: 30% (recent)
- 1-3 years old: 20% (cold)
- 3+ years old: 10% (archive candidates)

Largest Folders:
1. Videos: 32 GB (2,000 files)
2. 2024 Projects: 8 GB (600 files)
3. Reference Materials: 1.5 GB (400 files)

Duplicate Candidates: 8 files (5 GB combined)
```

### Step 2: Detect Duplicates Using Hash Comparison
**Find exact duplicates** (same content, different locations):

```bash
# MD5 hash all files (fast, good for duplicates)
find . -type f -exec md5sum {} + | sort | awk '{print $1}' | \
  uniq -d -w 32 | head -20
# Shows: Hash of duplicated files

# Get duplicate file paths
find . -type f -exec md5sum {} + > /tmp/hashes.txt
awk '{print $1}' /tmp/hashes.txt | sort | uniq -d > /tmp/dups.txt
while read hash; do
  grep "^$hash" /tmp/hashes.txt
done < /tmp/dups.txt
# Shows: All duplicate files grouped by hash
```

**Deduplication Decisions**:
```
Duplicate Set 1 (Hash: abc123...)
Size: 500 MB (total duplicate waste)
Files:
- ~/Documents/Resume_Final.pdf (Nov 2024)
- ~/Desktop/Resume_Final_V2.pdf (Nov 2024)
- ~/Archived/Resume_Final_FINAL.pdf (Oct 2024)

Decision: Keep most recent (Nov version), delete other 2 (saves 1 GB)

Duplicate Set 2 (Hash: def456...)
Size: 2 GB
Files:
- ~/Videos/Meeting_Recording.mp4 (Jan 2025)
- ~/Backup/Meeting_Recording.mp4 (Jan 2025)

Decision: Keep original location, delete backup copy
```

**Total Duplicate Waste**: 5 GB across 8 file sets

### Step 3: Choose Organization Strategy
**Strategy Selection Decision Tree**:

```
START: "How do I think about files?"
│
├─ "By what project I'm working on"
│  └─ STRATEGY: By Project
│     Structure: /2024-Q1_ClientX_Rebrand/ → /Strategy, /Design, /Code/
│     Best for: Agencies, consultants, project-based work
│
├─ "By file type" (docs, images, videos, code)
│  └─ STRATEGY: By Type
│     Structure: /Documents/, /Images/, /Videos/, /Code/
│     Best for: Personal files, long-term storage, minimalists
│
├─ "By date" (2024, 2025, by month)
│  └─ STRATEGY: By Date
│     Structure: /2025/03_March/, /2025/02_February/
│     Best for: Time-sensitive work, archives, journals
│
├─ "By purpose" (Active, Archive, Reference, Learning)
│  └─ STRATEGY: By Purpose
│     Structure: /Active/, /Archive/, /Reference/, /Learning/
│     Best for: Knowledge workers, students, developers
│
├─ "I have too many projects/categories"
│  └─ STRATEGY: Hybrid (Recommended)
│     Structure:
│     ├─ /Active_Projects/[Project-name]/
│     ├─ /Reference_Materials/[Topic]/
│     ├─ /Archive/[Year-Topic]/
│     └─ /Personal/[Category]/
│     Best for: Most people
│
└─ "I don't know, help me"
   └─ RECOMMEND: "By Purpose" (simplest, most flexible)
```

**Strategy Recommendation Based on Inventory**:
```
Folder Analysis:
- 2,000 video files
- 600 project files (from 8 different clients)
- Multiple year-old archives

RECOMMENDATION: Hybrid Strategy
Reasons:
- Videos belong in "Archive" (not frequently accessed)
- Client projects belong in "Active_Projects"
- Old files belong in "Archive/Year-Topic"
- Simple enough to maintain without tools

Proposed Structure:
/Main/
├─ Active_Projects/
│  ├─ 2025-Client_A_Website/
│  ├─ 2025-Client_B_Campaign/
│  └─ 2025-Personal_Portfolio/
├─ Archive/
│  ├─ 2024_Projects/
│  ├─ 2023_Projects/
│  └─ Reference_Materials/
└─ Personal/
   ├─ Resume/
   ├─ Finance/
   └─ Health/
```

### Step 4: Implement Naming Convention (YYYY-MM-DD Format)
**Standardized Naming** (makes files discoverable in listings):

**Format**: `YYYY-MM-DD_Name_Description.ext`

**Examples**:
```
Good:
2025-03-05_ProjectX_Wireframes_V3.figma
2025-02-28_Invoice_Acme_Corp_1500.pdf
2025-01-15_Meeting_Notes_TeamSync.docx
2024-12-20_Video_ProductDemo_3min.mp4

Bad (non-standard):
ProjectX_Wireframes.figma (no date, unmaintainable)
Final_FINAL_v2_ACTUAL.docx (meaningless versions)
2025-03-05 Invoice for Acme.pdf (space in filename, harder to parse)
meeting notes.docx (no date, lowercase, ambiguous)

Why date-first:
- Sorted chronologically (os.listdir() shows by date)
- Find by timeframe instantly (all files from March 2025)
- Clear version progression (V1 → V2 → V3 shows evolution)
- Email-safe (avoids issues with spaces)
```

**Batch Rename Script**:
```bash
# Rename all files to YYYY-MM-DD format based on modification date
for file in *; do
  if [ -f "$file" ]; then
    # Get modification date in YYYY-MM-DD
    date=$(stat -f%Sm -t%Y-%m-%d "$file")  # macOS
    # For Linux: date=$(stat -c%y "$file" | cut -d' ' -f1)

    # Extract extension
    ext="${file##*.}"

    # Remove old date if present
    name=$(echo "$file" | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}_//g')

    # Rename with new date prefix
    mv "$file" "${date}_${name}"
  fi
done
```

**Naming Convention Rules**:
- Start with date: YYYY-MM-DD (sortable, clear)
- Use underscores (not spaces): Easy to parse, shell-friendly
- Include context: [Project_Topic_Description]
- Add version if relevant: V1, V2 (not "final_final")
- End with extension: .pdf, .docx, .mp4
- Keep under 60 characters (readable in file dialogs)

### Step 5: Archive Strategy (Active vs Cold Storage)
**Definition**:
- **Active Storage**: Files accessed at least once per month
- **Cold Storage**: Files not accessed in 6+ months
- **Archive**: Project-complete, legally required to keep (tax, contract), historical reference

**Archive Decision Matrix**:
```
                    | Recently Used | Old | Not Used
                    |    (< 1mo)    | (1-6mo) | (6+ mo)
  ──────────────────┼──────────────┼────────┼──────────
  Small (< 500MB)   | Keep Local   | Keep   | Archive
  Medium (500MB-2GB)| Keep Local   | Archive| Archive
  Large (2GB+)      | SSD/Fast     | Archive| Cold Cloud

Examples:
- Recent project (2025, active): /Active_Projects/
- Completed project (2024): /Archive/2024/
- Old videos (2020-2022): Cold storage (AWS S3 / Backup drive)
```

**Archival Process**:
```
Step 1: Identify archive candidates
find . -type f -mtime +180  # Not modified in 6 months

Step 2: Group by category
/Archive/2023_Projects/ (20 GB)
/Archive/Reference_Materials/ (5 GB)
/Archive/Personal_Old/ (2 GB)

Step 3: Move to cold storage
Option A: External drive (cheapest, manual)
Option B: Cloud storage (AWS S3 Glacier, $1/month for 100GB)
Option C: NAS backup (reliable, accessible)

Step 4: Create manifest (what was archived, where, why)
Date Archived: 2025-03-05
Category: 2023_Projects
Size: 20 GB
Location: /Volumes/BackupDrive/Archive/2023_Projects/
Retention: Until 2026-12-31 (3 years)
Reason: Tax documentation, contractual requirement
```

### Step 6: Folder Structure Templates (Reusable)
**Template 1: Client Project Folder**
```
/2025-Q1_ClientX_Website/
├─ 01_Briefs/
│  ├─ 2025-01-10_ClientBrief_Requirements.pdf
│  └─ 2025-01-12_Sitemap_Approved.pdf
├─ 02_Design/
│  ├─ Wireframes/
│  │  ├─ 2025-01-15_Wireframes_V1.figma
│  │  └─ 2025-01-20_Wireframes_V2_Final.figma
│  └─ Visual_Design/
│     ├─ 2025-02-01_Style_Guide.pdf
│     └─ 2025-02-05_HighFi_Mockups.figma
├─ 03_Development/
│  ├─ Code/ (GitHub repo link or code files)
│  ├─ Assets/ (images, fonts, icons)
│  └─ 2025-03-01_Testing_Checklist.md
├─ 04_Communications/
│  ├─ 2025-01-12_Kickoff_Notes.md
│  ├─ 2025-02-15_StatusReport_Feb.pdf
│  └─ 2025-03-01_Handoff_Notes.md
└─ 05_Deliverables/
   ├─ 2025-03-05_Website_Live.txt (URL)
   └─ 2025-03-05_Client_Documentation.pdf

Rationale: Phases in order (Brief → Design → Dev → Deliver)
Future: Easy to archive entire folder on completion
```

**Template 2: Personal Knowledge Management**
```
/Learning/
├─ 01_Active_Courses/
│  ├─ 2025_Python_Advanced/
│  │  ├─ 2025-02-15_Lecture_1_Notes.md
│  │  ├─ 2025-02-20_Assignment_1_Code.py
│  │  └─ 2025-03-01_Lecture_2_Notes.md
│  └─ 2025_System_Design/
│     ├─ Readings/ (PDFs, articles)
│     └─ Notes/ (my summaries)
├─ 02_Reference_Materials/
│  ├─ Python_Docs/
│  ├─ Design_Systems/
│  └─ DevOps_Best_Practices/
└─ 03_Projects_Built/
   ├─ 2024_BuildWeather_App/
   ├─ 2024_DataPipeline_Project/
   └─ 2025_APIServer_Tutorial/

Rationale: Separates active learning from archived knowledge
Future: Move completed courses to Archive yearly
```

**Template 3: Developer Portfolio/Repository**
```
/Dev/
├─ 01_Active_Projects/
│  ├─ 2025-Website_Redesign/ (GitHub link)
│  ├─ 2025-API_Service/ (GitHub link)
│  └─ 2025-Learning_Project/ (GitHub link)
├─ 02_Archived_Projects/
│  ├─ 2024_Completed_Features/
│  └─ 2023_Archived_Repos/
├─ 03_Code_Snippets/
│  ├─ Authentication_Examples/
│  ├─ Database_Queries/
│  └─ DevOps_Scripts/
├─ 04_Documentation/
│  └─ How_To_Guides/
└─ 05_Scratch/
   └─ Experiments_Temporary/

Rationale: Active projects at top, code snippets searchable, scratch for testing
Future: Clean up "Scratch" folder monthly
```

### Step 7: Batch Renaming and Moving
**Safe Batch Processing** (don't lose files):

```bash
# Dry-run first (see what would happen, don't execute)
find ./OldFolder -type f -name "*.pdf" | while read file; do
  newname="$(date -r "$file" +%Y-%m-%d)_$(basename "$file")"
  echo "Would move: '$file' → '$newname'"
done > dry_run.txt
# Review dry_run.txt before executing

# Actual batch move with date prefix
find ./OldFolder -type f -name "*.pdf" | while read file; do
  newname="$(date -r "$file" +%Y-%m-%d)_$(basename "$file")"
  mv "$file" "$newname"
  echo "Moved: $file"
done

# Move all to destination
mkdir -p /NewStructure/Documents
mv *.pdf /NewStructure/Documents/
```

**Safe Deduplication**:
```bash
# Back up before removing duplicates
cp -r /OldFolder /OldFolder.backup

# Remove duplicates (keep first, delete rest)
find . -type f -exec md5sum {} + | sort | uniq -d -w 32 | while read hash file; do
  rm "$file"
  echo "Deleted duplicate: $file"
done
```

### Step 8: Maintain Structure (Ongoing)
**Monthly Maintenance** (15 minutes):

```
1. Check inbox/download folder (2 min)
   - Move categorized files to permanent locations
   - Delete temporary files, empty recycle bin

2. Rename recent files to date format (3 min)
   - Recent files not following naming convention?
   - Batch rename them

3. Review "Scratch" folder (5 min)
   - Experiments/temp files from month
   - Keep useful ones, delete rest

4. Check for duplicate file sizes (5 min)
   - Any suspiciously similar-sized files?
   - Quick spot check

Monthly checklist:
- [ ] Downloads folder cleared
- [ ] Active projects organized
- [ ] Duplicates removed
- [ ] Naming convention applied
```

### Step 9: Metadata Preservation
**Keep original timestamps when reorganizing**:

```bash
# Move file but preserve modification date
touch -r "/source/file.pdf" "/destination/file.pdf"

# Batch preserve metadata
for file in /OldLocation/*; do
  cp --preserve=timestamps "$file" /NewLocation/
done

# Alternative: Use rsync (preserves all metadata)
rsync -av --delete /OldLocation/ /NewLocation/
# -a: archive mode (preserves timestamps, permissions)
# -v: verbose (shows progress)
# --delete: removes files in destination not in source
```

**Create Manifest** (backup of original structure):
```
Manifest: 2025-03-05_Reorganization.txt

Original Structure:
/Documents/Random/
  - 2025_ProjectX_Wireframes.pdf
  - 2025_ProjectX_HighFi.pdf
  - old_wireframes_v1.pdf

New Structure:
/Active_Projects/2025-ProjectX/
  - 02_Design/
    - 2025-01-15_Wireframes_V1.pdf
    - 2025-02-01_Wireframes_V2_Final.pdf
    - 2025-02-05_HighFi_Mockups.pdf

Deletions: old_wireframes_v1.pdf (duplicate, archived)
```

### Step 10: Automate Recurring Tasks
**Folder Monitoring** (optional, for frequent reorganizers):

```bash
# Monthly archive cleanup (runs first day of month)
#!/bin/bash
# Run via cron: 0 9 1 * *

echo "=== Monthly File Organization ===" >> ~/file_org.log

# Move old files to archive
find ~/Documents -type f -mtime +180 | while read file; do
  mv "$file" ~/Archive/
  echo "Archived: $(basename $file)" >> ~/file_org.log
done

# Clean downloads folder
find ~/Downloads -type f -mtime +30 -delete
echo "Cleaned downloads folder" >> ~/file_org.log

# Remove duplicates
find ~ -type f -exec md5sum {} + | sort | uniq -d -w 32 | \
  while read hash file; do
    rm "$file"
    echo "Deleted duplicate: $file" >> ~/file_org.log
  done

date >> ~/file_org.log
```

## Output Template

```
File Organization Plan
======================
Folder: [Path]
Analysis Date: [Today]
Total Size: [X GB]
File Count: [Y]

Current State:
- Size by type: [Breakdown]
- Files by age: [Breakdown]
- Organization: [Current chaos level]
- Duplicates: [X GB of waste]

Proposed Structure:
[ASCII tree of new structure]

Implementation Steps:
1. Back up original folder
2. [Step 2]
3. [Step 3]
...

Estimated Savings:
- Space freed: [X GB]
- Time to find files: [X min → Y min]
- Naming convention: Applied to Y files

Maintenance:
- Monthly tasks: [List]
- Tools needed: [List]
- Estimated time/month: [X minutes]
```

## Quality Gates

1. **Backup created before any moves**: Never reorganize without safety copy
2. **Naming convention applied consistently**: 100% of moved files follow YYYY-MM-DD format
3. **Duplicates identified and removed**: Used cryptographic hashing, not just filename
4. **Structure matches user's actual workflow**: Not generic; reflects how they think
5. **Folder depth reasonable**: 3-4 levels max (deeper = harder to navigate)
6. **Total folder size reduced by 5-15%**: Duplicates removed
7. **Maintenance plan documented**: How to keep it organized going forward

## Examples

### Good: Before/After Organization
```
BEFORE:
/Documents/
├─ Stuff/
├─ New Folder/
├─ Projects/
│  ├─ ClientA/
│  ├─ Client A/
│  ├─ client_a_old/
│  └─ ProjectB_2023/
├─ Resume.pdf
├─ Resume_Final.pdf
├─ Resume_FINAL_v2.pdf
└─ Random\ Folder/

Space: 45 GB, 3,200 files, very messy

AFTER:
/Documents/
├─ Active_Projects/
│  ├─ 2025-ClientA_Website/ (5 GB, current project)
│  └─ 2025-ClientB_App/ (2 GB, current project)
├─ Archive/
│  ├─ 2024_Projects/ (15 GB, completed work)
│  └─ 2023_Projects/ (12 GB, completed work)
├─ Personal/
│  ├─ Resume/ (2025-03-05_Resume_Final.pdf only)
│  └─ Reference/ (1 GB, useful materials)
└─ Scratch/ (temp files, cleaned monthly)

Space: 37 GB (8 GB duplicates removed), 2,100 files, clear structure

Time to find file:
- Before: "Is Resume in Documents or Projects?... 30 minutes of searching"
- After: "In Personal/Resume/2025-03-*" found in 20 seconds
```

### Bad: Over-Complicated Structure
```
/Documents/
├─ 2025/
│  ├─ 01_January/
│  │  ├─ 01_Work/
│  │  │  ├─ Projects/
│  │  │  │  ├─ ClientA/
│  │  │  │  │  ├─ Emails/
│  │  │  │  │  ├─ Designs/
│  │  │  │  │  └─ Development/

Problems:
- 6 levels deep (slow to navigate)
- Mixed date (year/month) with category
- Overly granular
- Would take 30 minutes monthly to maintain
```

## Common Mistakes

1. **Organizing before deduplicating**: Creating structure with 30% duplicate files wastes space. Always deduplicate first.

2. **Using generic names**: "Final", "FINAL_v2", "ACTUAL_FINAL" creates confusion. Use dates and version numbers instead.

3. **Too many top-level folders**: 50+ folders = hard to navigate. Limit to 5-8 main categories.

4. **Forgetting to back up first**: Reorganizing without backup is risky. One wrong mv command = lost files.

5. **Organizing while actively developing**: Files get reorganized, then created in old location. Wait until project completes, then organize.

6. **Structure doesn't match workflow**: Creating structure that's logically perfect but nobody uses it. Ask the user first: "How do you think about files?"

## Anti-Patterns

1. **Endless nesting**: More than 3-4 levels deep means users are spending time navigating folders, not working.

2. **Temporal + categorical mix**: "2025/Projects/ClientA" is confusing (which level for searching?). Pick one primary axis.

3. **No deduplication**: Keeping "file_final.pdf" AND "file_final_2.pdf" = wasted space, confusion.

4. **Reorganizing too frequently**: If structure changes monthly, users never learn it. Lock in structure for 6-12 months before changing.

5. **Archive folder that's never pruged**: Archive grows indefinitely. Set retention policies (keep 3 years, then delete).

6. **Not naming files during creation**: Asking to rename 2,000 files later = tedious. Establish naming convention BEFORE work starts.
