# Gann book source comparison — 2026-10-23

Scope: original searchable English text compared with available Nepali PDFs, chapters 1–15. This is a **structural / coverage audit**, not a line-by-line translation accuracy certification.

## Source coverage
| Chapter | English source text characters (approximately) | Nepali file status |
|---|---:|---|
| 1 | 7,415 | PDF exists with foreword |
| 2 | 17,620 | PDF exists |
| 3 | 24,450 | PDF exists |
| 4 | 20,752 | PDF exists |
| 5 | 18,189 | PDF exists (much biblical material left in English; examine carefully) |
| 6 | 21,504 | PDF exists |
| 7 | 13,587 | PDF exists |
| 8 | 6,728 | PDF exists |
| 9 | 24,121 | PDF exists |
| 10 | 15,869 | PDF exists |
| 11 | 17,266 | PDF exists |
| 12 | 44,459 | **partial only** |
| 13 | 22,135 | **partial only** |
| 14 | 24,340 | **partial only** |
| 15 | 12,621 | **no Nepali file** |

**Important:** Existence of an existing PDF does not prove that every sentence and quotation of the source was translated accurately. A full source-to-target paragraph alignment review is still required for chapters 1–11. Some PDF text extraction is imperfect with Nepali script, so automated string comparison alone cannot establish translation fidelity.

## Changes needed, not wholesale replacement
- Keep all existing PDFs unchanged pending verified, specific corrections.
- Complete only missing source content of chapters 12–14, then translate chapter 15.
- Compare every paragraph, number, dates, headings, poems, letters and biblical quotations from the main book. Do not add interpretations.
- Revise only paragraphs shown to be missing or mistranslated.
- Rebuild changed PDFs and visually inspect Devanagari rendering.
- Upload final PDFs into `Gann/Books/` with authenticated binary-capable Git tooling. **No binaries have been pushed** using this connector.

This file documents comparison results; it does NOT claim that chapters 12–15 are final or that a word-by-word verification has been completed.

## 2026-10-23 later update
- Chapter 15 Nepali narrative draft has now been created as a 4-page PDF (`WD_Gann_Tunnel_Nepali_Ch15.pdf`). Original English poems and scriptural quotations are retained, as requested for difficult-to-translate text.
- It is not independently certified as exact; original paragraph-by-paragraph checks remain.
- Chapters 12–14 remain **partial**, and chapters 1–11 have not been certified after full line-by-line comparison.
- Updated ZIP in working files: `Rudra_Gann_Books_Through_Ch15_Updated.zip` (not uploaded to GitHub).


## Automated chapter-span audit — 2026-10-23
Source lengths measured on original searchable English chapters; PDF character counts are extraction lengths, **not** translation completeness proofs.

| Ch | English chars | Nepali extracted chars | State |
|---|---:|---:|---|
| 1 | 7415 | 8326 | file exists; not certified |
| 2 | 17620 | 12809 | file exists; not certified |
| 3 | 24450 | 19039 | file exists; not certified |
| 4 | 20752 | 19301 | file exists; not certified |
| 5 | 18189 | 17250 | file exists; not certified |
| 6 | 21504 | 18835 | file exists; not certified |
| 7 | 13587 | 12471 | file exists; not certified |
| 8 | 6728 | 6202 | file exists; not certified |
| 9 | 24121 | 20542 | file exists; not certified |
| 10 | 15869 | 13282 | file exists; not certified |
| 11 | 17266 | 14258 | file exists; not certified |
| 12 | 44459 | 1921 | partial |
| 13 | 22135 | 2606 | partial |
| 14 | 24340 | 2444 | partial |
| 15 | 12621 | 11985 | file exists; not certified |

Full original English reference PDFs for chapters 12–15 and all available Nepali drafts are available in the working verification ZIP package, **not committed as binaries in Git**. Do not state that chapter 12–14 translations are complete.
