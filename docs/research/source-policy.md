# Research and media source policy

Verified: 2026-07-23

## Evidence hierarchy

Prefer, in order:

1. official product documentation, company filings, standards, and source code;
2. original peer-reviewed papers/preprints and official project repositories;
3. authoritative public repositories that preserve license provenance;
4. secondary reporting, clearly identified as secondary.

Record access/verification date. Label conclusions `confirmed`, `inference`, or
`unknown`; never turn an inference into a vendor statement.

## Public benchmark admission

Admit only media whose video itself has a clear grant permitting adaptation and
public display: CC0, public domain, CC BY, or deliberately accepted CC BY-SA.
Exclude NC, ND, research-only, ambiguous “free,” and cases where only background
music—not the video—is Creative Commons.

Prefer Wikimedia Commons, government repositories, Internet Archive, Zenodo,
or a creator-provided download with explicit terms. A source URL or attribution
alone is not permission.

Creative Commons does not automatically clear privacy, publicity, trademark,
location, performance, or third-party audio rights. Review content before any
public demo; mute or replace questionable audio. Preserve required attribution,
license links, change notices, and ShareAlike terms.

## Storage and acquisition

External data lives outside Git under the root configured by `AEGIS_DATA_DIR`.
Do not hard-code a user-specific absolute path. A future acquisition command
must be explicit and user-invoked; tests and normal processing must never
download assets.

Until acquired and probed, keep `direct_url`, `sha256`, codec details, frame
rate, audio details, and projection verification marked pending. After
acquisition, record the source page, immutable or direct URL, access date,
checksum, `ffprobe` output or normalized media facts, and acquisition method.

Never commit benchmark video, user footage, proxies, extracted frames, audio,
identity embeddings, or generated outputs. A manifest records provenance; it is
not a downloader or a substitute for license compliance.

## YouTube

Do not use an arbitrary YouTube upload merely because it is publicly viewable.
For retained benchmark items, use the copy and preserved license evidence on an
authoritative repository such as Wikimedia Commons. This avoids relying on a
current YouTube UI state and avoids making implicit YouTube downloads part of
the project workflow.
