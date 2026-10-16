# Climbing data sources

This document records the source-of-truth and permission decisions for the ClimbIQ logbook pivot. The objective is to give users one history without quietly scraping or locking that history into another proprietary service.

## Mountain Project

### Production decision

ClimbIQ imports a CSV explicitly exported by the signed-in Mountain Project user. It does not crawl route pages, call private endpoints, or ask for Mountain Project credentials.

Mountain Project documents the export flow as:

1. Sign in on the Mountain Project website.
2. Open the user's profile.
3. Open **View All** beside **Ticks**.
4. Select **Export CSV**.

Reference: <https://www.mountainproject.com/help/27/overview-of-mountain-project-features>

The current CSV columns are:

```text
Date, Route, Rating, Notes, URL, Pitches, Location, Avg Stars,
Your Stars, Style, Lead Style, Route Type, Your Rating, Length, Rating Code
```

ClimbIQ keeps the route URL and numeric route ID where present, classifies `Fell/Hung` and similar styles as attempts, and treats other ticks as sends. Each imported row gets a stable fingerprint so the same export can be imported again without duplication.

### Why there is no live route sync

Mountain Project's old public data API is no longer available. Its current Terms of Use prohibit spiders, crawlers, scrapers, and similar automated tools from substantially downloading or archiving the service. The user-owned CSV is therefore the supported boundary for this version.

Terms: <https://www.adventureprojects.net/ap-terms>

If a future live integration is desired, it should use a written data agreement with onX/Mountain Project rather than page scraping.

## MoonBoard

### Official source

The official MoonBoard app is the sanctioned complete catalog and logbook. Moon Climbing's FAQ currently states that it does not share the MoonBoard dataset.

Reference: <https://moonclimbing.com/using-moonboard-app>

ClimbIQ therefore does not connect to MoonBoard credentials or private app endpoints. Users can log MoonBoard 2016 climbs at 40° manually today, including problem name, grade, result, and notes. The setup is deliberately fixed so future catalog records cannot be mixed across incompatible hold layouts.

### Community catalog candidates

Two community projects demonstrate that useful catalog data exists:

- Boardhang publishes an MIT-licensed open-source app and curated MoonBoard snapshots covering several setups: <https://github.com/boardhang/boardhang-app>
- Boardsesh publishes developer documentation and a public-read catalog API: <https://www.boardsesh.com/docs>

Boardsesh's documentation also says that a published app using its backend as a service needs written permission, which it does not currently grant. ClimbIQ will not depend on that live backend in production without permission.

### Catalog adapter contract

The database model is ready for a later catalog importer. A catalog problem maps to:

```text
source              moonboard
external_id         stable catalog identifier
name                problem name
grade               Font grade
grade_system        Font
board_name          MoonBoard 2016
board_angle         40
setter              attributed setter
is_benchmark        benchmark flag
metadata_json       holds, rating, repeats, source revision
```

User logbook entries point to that canonical climb record. Changing the upstream catalog will not rewrite or delete the user's historical sends and attempts.

## Rollout checklist

- [x] Unified outdoor and MoonBoard logbook schema
- [x] Manual logging for both disciplines
- [x] Mountain Project CSV import with duplicate protection
- [x] Source links and provenance retained per climb
- [x] Combined progress summary and timeline
- [x] Confirm target setup: MoonBoard 2016 at 40°
- [ ] Obtain written permission for a live catalog, or select a redistributable versioned snapshot
- [ ] Add catalog attribution, revision, and removal policy
- [ ] Add problem search and hold diagrams
- [ ] Add full ClimbIQ JSON/CSV export

This is an engineering record, not legal advice. Provider terms and permissions should be rechecked before every production catalog refresh.
