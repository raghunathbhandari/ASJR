# Rudra-Gann — Operational Handoff
Last updated: 2026-10-23 (UK)

## Project
Faithful Nepali translation of W.D. Gann's 1927 *The Tunnel Thru the Air (or Looking Back from 1940)*, using the searchable Project Gutenberg-derived English text as the working source. The original 1927 scanned edition has different pagination.

## Mandatory translation rules
- Translate **all** original content, paragraph by paragraph, in original order; no summaries, additional theories, invented dialogue, or interpretation.
- Preserve original names, dates, numerical values, mathematical/astrological references, letter text and ordering.
- If a phrase is awkward or loses its meaning in Nepali, retain the **original English phrase** rather than forcing a literal Nepali rendering.
- Preserve poetic passages and biblical quotations in English as appropriate; do not remove them.
- Do not label a chapter complete until its source span is fully covered and text has been compared against the original.
- Ensure selectable Devanagari text and visually inspect generated PDF pages.

## Existing artifacts (not yet committed to Git)
The PDFs were generated in the ChatGPT workspace / Library, not yet committed as binaries in this Git repository:
- `WD_Gann_Tunnel_Thru_the_Air_Searchable.pdf` — searchable English working edition
- `WD_Gann_Tunnel_Nepali_Part1.pdf` — foreword + Chapter 1, corrected awkward biblical quotation
- `WD_Gann_Tunnel_Nepali_Ch2.pdf`
- `WD_Gann_Tunnel_Nepali_Ch3.pdf`
- `WD_Gann_Tunnel_Nepali_Ch4.pdf`
- `WD_Gann_Tunnel_Nepali_Ch5.pdf`
- `WD_Gann_Tunnel_Nepali_Ch6.pdf`
- `WD_Gann_Tunnel_Nepali_Ch7.pdf`

Chapters 8 and 9 have now been generated as separate Nepali PDFs. Chapters 10 and 11 have also been generated on 2026-10-23; their translations should be checked paragraph-by-paragraph against the English original before publishing as fully verified.

## New PDFs, chapters 8–11
- `WD_Gann_Tunnel_Nepali_Ch8.pdf`
- `WD_Gann_Tunnel_Nepali_Ch9.pdf`
- `WD_Gann_Tunnel_Nepali_Ch10.pdf`
- `WD_Gann_Tunnel_Nepali_Ch11.pdf`

## Git upload TODO
Transfer the above PDFs to `Gann/Books/` using binary-capable authenticated Git tooling. GitHub's current text-file connector cannot directly ingest the workspace's PDF bytes. Do **not** claim these binary artifacts were uploaded by this documentation commit.
Suggested names under `Gann/Books/` are the existing names above.

## User workflow
User requests the next chapter by number only (e.g. “8”). Return the complete Nepali chapter PDF with minimal prose, linking only a verified artifact.

## Related Rudra-Gann research (kept separate from book translation)
INTC 4H: Gann Fan, Gann Box, Square, historical turning-price levels; independently test prices against real OHLC data. Do not add trading interpretation into translated books.
