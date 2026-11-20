# Mini Project Report: Build Guide and Template
*(CSD 300 / CSD 301 / CSD 302 / ECD 301 / ECD 302, IEEE-style referencing)*

> Use this file as a checklist and a skeleton. Replace everything in `[square brackets]`. Copy the formatting rules into your Word/LaTeX template **before** you start writing.

---

## 0. Quick Formatting Rules (set these up first)

| Item | Rule |
|---|---|
| Margins (inches) | Top **1**, Bottom **1.25**, Left **1.5**, Right **0.8** |
| Font | Times New Roman |
| Chapter heading | Starts on a **fresh page**, extra top margin of about **75 mm** |
| Chapter number + title | Centered, **bold**, upper and lower case (no all-caps / small-caps), see note below on size |
| Vertical gaps | About **25 mm** between chapter number and title, and between title and first paragraph |
| Numbering | Arabic numerals for chapters, continuous through the report (1, 2, 3...) |
| Sections | Decimal numbering: `2.2`, `2.3.4` |
| Table caption | **Above** the table, with number (e.g., *Table 3.1*) |
| Figure/graph caption | **Below** the figure, with number (e.g., *Figure 6.4*) |
| Table/figure numbering | Chapter-wise: 4th figure in Chapter 6 = **Figure 6.4** |
| Figures | Drawn with drafting software only. **No freehand, no photocopies/scans** of figures, graphs, tables or photos from references |
| Reused material | Cite the source in a **separate last line** of the caption |
| Equations | Typed (Equation Editor / LaTeX). If handwritten, leave ample space and use permanent black ink |
| Binding (evaluation copy) | Spiral or soft bound |
| Submission | Hard copy to **Supervisor** and **Institute Library** |

> **Heads-up, guideline conflict:** Section 1.1 says chapter heading = *16 pt, all caps, bold, centered*, while Section 4.1 says *18 pt, bold, upper and lower case (no all-caps)*. The detailed format section (4.1) is the usual one to follow, but **confirm with your supervisor** and use one style consistently.

---

## 1. Order of Contents (bind in exactly this sequence)

### Part A: no page numbers
1. Cover page (with copyright)
2. Declaration-I
3. Declaration-II
4. Certificate page
5. Acknowledgment

### Part B: lower-case Roman numerals (i, ii, iii...), starting at the Abstract
6. Abstract (**one page only**)
7. Table of Contents
8. List of Figures
9. List of Tables
10. List of Symbols, Abbreviations or Nomenclature

### Part C: Arabic numerals, starting at Chapter 1
11. Chapters
12. References
13. Appendices
14. List of Publications *(if any)*
15. Photocopy of published papers *(if any)*
16. Facsimile of industry certificate *(only for industry-based projects)*
17. Photocopy of award-winning certificates for technical competitions *(if any)*

---

## 2. Front Matter Templates

### 2.1 Cover Page
```
                    [TITLE OF THE MINI PROJECT]

              A Mini Project Report submitted in partial
        fulfilment of the requirements for the course [CSD/ECD 30X]

                               by

            [Student 1 Name]   [Roll No.]
            [Student 2 Name]   [Roll No.]
            [Student 3 Name]   [Roll No.]

                       Under the guidance of
                     [Supervisor Name, Designation]

               [Department Name]
               [Institute Name]
               [City, State]
               [Month Year]

               © [Institute Name / Group], [Year]
```

### 2.2 Declaration-I (by the student group)
```
DECLARATION

We hereby declare that this report titled "[Title]" is a record of original work
carried out by us under the supervision of [Supervisor Name]. The matter embodied
in this report has not been submitted elsewhere for any degree or diploma. All
sources used have been duly acknowledged.

[Name, Roll No., Signature]  ...                       Date:
                                                       Place:
```

### 2.3 Declaration-II
> Use the exact format/wording your institute provides (for example, the supervisor's/guide's declaration, or the plagiarism/originality declaration). **Ask your supervisor or department for the template.** Insert it here.

### 2.4 Certificate Page
```
CERTIFICATE

This is to certify that the Mini Project Report entitled "[Title]" submitted by
[Names, Roll Nos.] to [Institute Name] in partial fulfilment of the requirements
of [Course Code] is a bonafide record of the work carried out by them under my
supervision.

[Supervisor Name]                      [Head of Department]
[Designation]                          [Department]
Date:                                  Place:
```

### 2.5 Acknowledgment
Short (one page). Thank the supervisor first, then lab staff, department, family and teammates. Sign off with names and date.

### 2.6 Abstract (ONE page only)
Write in this order, 200 to 300 words:
1. **Problem**: what and why (1 to 2 sentences)
2. **Approach**: method/design/tools used (2 to 3 sentences)
3. **Key results**: the main numbers (2 sentences)
4. **Conclusion**: significance (1 sentence)

`Keywords: [keyword1], [keyword2], [keyword3], [keyword4]`

### 2.7 Table of Contents
- Include Chapters, Sections and Subsections, **page numbers flush right**.
- Auto-generate from heading styles (Heading 1 = Chapter, Heading 2 = Section, Heading 3 = Subsection).

### 2.8 List of Figures / List of Tables
```
Figure 1.1   [Caption]  ................................................ 3
Figure 3.2   [Caption]  ................................................ 17
```
```
Table 3.1    [Caption]  ................................................ 15
```

### 2.9 List of Symbols, Abbreviations or Nomenclature
| Symbol / Abbreviation | Meaning | Unit (if any) |
|---|---|---|
| [e.g., `f_r`] | [Resonant frequency] | [GHz] |
| [e.g., DGS] | [Defected Ground Structure] | - |

---

## 3. Chapters

> The **first** chapter must be *Introduction*; the **last** must be *Summary and Conclusions*. All middle chapters get precise, content-reflecting titles. A suggested layout is below; rename middle chapters to suit your project.

### CHAPTER 1: Introduction
- 1.1 Background / Problem statement (brief statement of the problem investigated)
- 1.2 Motivation: justify and highlight why the problem matters
- 1.3 Objectives and Scope of Work (define the topic, aim and scope)
- 1.4 Significant Contributions / Importance of the Investigation
- 1.5 **Organization of the Report**: one short summary per chapter

```
Chapter 1 introduces ...  Chapter 2 reviews ...  Chapter 3 describes ...
Chapter 4 presents ...    Chapter 5 summarises ...
```

### CHAPTER 2: Literature Review
- Significant review of previously published work on your topic. Group by theme, not paper by paper.
- Cite every source with IEEE-style numbers, e.g., "as reported in [3]".
- Optional: a comparison **table** of prior work (caption above the table).
- **The final paragraph must state the work to be carried out in light of this review** (the gap you address).

### CHAPTER 3: Proposed Work *(rename to fit, e.g., "System Design and Methodology")*
- Procedures adopted, techniques/methodologies developed and adopted, experimental setups.
- **Every subsection needs a suitable title.**
- Keep derivations **short and important**; include representative data in tables and figures.
- Move lengthy derivations, voluminous tables and large numbers of figures to the **Appendix**.
- Suggested subsections: 3.1 Overview / Block diagram, 3.2 Design, 3.3 Implementation, 3.4 Experimental setup.

### CHAPTER 4: Results and Discussions
- Methodical evaluation of the investigation; present the contributions of the study.
- Use tables and figures (with chapter-wise numbering) for results.
- Discuss logically, so that discussion leads to **inferences and conclusions** and to the **scope for future work**.
- Compare against literature/expected values where possible.

### CHAPTER 5: Summary and Conclusions *(final chapter)*
Present **each point separately** (numbered/bulleted):
1. **Summary** of the work carried out (brief, first part)
2. **Conclusions** derived from the analysis in Chapter 4
3. **Scope for future work** (clearly stated, last part)

---

## 4. Tables, Figures, Equations: Format Examples

**Table (caption ABOVE):**
```
Table 4.1: Comparison of simulated and measured results

| Parameter | Simulated | Measured |
|-----------|-----------|----------|
| ...       | ...       | ...      |
Source: [12]        <- separate last line, only if reproduced from a reference
```

**Figure (caption BELOW):**
```
[figure drawn in drafting software]
Figure 3.2: Block diagram of the proposed system
Source: [7]         <- separate last line, only if reproduced from a reference
```

**Equation (numbered, right-aligned):**
```
E = mc^2                                              (3.1)
```
Refer to it in the text as "(3.1)", and define every symbol on first use.

---

## 5. References (IEEE numbered style)

Rules from the guidelines:
- Number all references.
- List them **sequentially in the order they first appear in the text** (IEEE order of citation).
- **Every listed reference must be cited in the text**, using `[1]`, `[2]`, etc.
- Book: author(s), title, edition, chapter number, page numbers, publisher, location, year.
- Journal/conference paper: authors, title, journal/conference name, volume and issue (journal), page numbers, month and year.
- Web page: author or company name and the URL.

**Templates and examples (copy this pattern):**

```
Book:
[1] Constantine A. Balanis, Antenna Theory: Analysis and Design, 3rd Ed., Ch. 6,
    pp. 318-322, John Wiley and Sons, Canada, 2005.

Journal:
[2] M. Fan, R. Hu, Z. H. Feng, X. X. Zhang, and Q. Hao, "Advance in 2D-EBG structures
    research," The Journal of Infrared and Millimeter Waves, vol. 22, no. 2, 2003.

Conference:
[3] J. A. Tirado-Mendez, M. A. Peyrot-Solis, H. Jardon-Aguilar, E. A. Andrade-Gonzalez,
    and M. Reyes-Ayala, "Applications of novel defected microstrip structure (DMS) in
    planar passive circuits," in Proc. 10th WSEAS Int. Conf. Circuits, Vouliagmeni,
    Athens, Greece, pp. 336-369, Jul. 10-12, 2006.

Web page:
[4] [Author/Company], "[Page title]," [Site name]. [Online]. Available: [URL]
```

> **Note:** The guidelines also say "use a chronological bibliography". In IEEE style, ordering by first citation in the text is the standard; keep the numbering sequential as cited. Confirm with your supervisor if they want strict year-wise ordering instead.

---

## 6. Appendices

- Hold detailed information, lengthy derivations, raw experimental observations, code listings, etc.
- Number with **Roman capitals**: *Appendix I, Appendix II, Appendix III...*
- References cited inside appendices must also appear in the main References list (the guidelines say these come first in the "Literature Cited" section, so cite them before other references where applicable).

```
APPENDIX I:   [Detailed derivation of ...]
APPENDIX II:  [Raw experimental data]
APPENDIX III: [Source code]
```

---

## 7. Back Matter (only if applicable)

- **List of Publications**: papers/technical notes on the project topic by the group. Use IEEE reference format.
- **Photocopy of published papers**: reprints placed after the list.
- **Industry certificate facsimile**: only for industry-based projects.
- **Award certificates**: for technical competitions, if any.

---

## 8. Final Submission Checklist

**Structure**
- [ ] Contents are in the exact sequence of Section 1 above
- [ ] Part A has no page numbers; Part B uses i, ii, iii...; Part C uses 1, 2, 3... from Chapter 1
- [ ] Abstract is exactly one page
- [ ] Chapter 1 is *Introduction* (ends with Organization of the Report); last chapter is *Summary and Conclusions*
- [ ] Literature Review ends with the planned work/gap paragraph
- [ ] Future scope stated at the end of the final chapter

**Formatting**
- [ ] Margins: T 1", B 1.25", L 1.5", R 0.8"
- [ ] Each chapter starts on a new page with about 75 mm top margin; about 25 mm gaps after number and title
- [ ] Chapter heading style confirmed with supervisor (16 pt vs 18 pt)
- [ ] Table captions above, figure captions below, numbered chapter-wise
- [ ] All figures made in drafting software, with no scans or photocopies from references
- [ ] Reused figures/tables have a source line in the caption
- [ ] Equations typed and numbered

**References**
- [ ] Every reference is cited in the text and numbered in order of appearance
- [ ] Format matches the book / journal / conference / web examples
- [ ] Appendix citations included

**Delivery**
- [ ] Plagiarism check done (if your institute requires one)
- [ ] Supervisor has reviewed and signed the certificate
- [ ] Hard copy (spiral or soft bound) submitted to Supervisor **and** Institute Library
