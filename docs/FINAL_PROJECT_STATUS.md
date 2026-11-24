# SAFARNAMA project status

**Verified local application using supplied Delhi static data.** The planner
supports direct and one-transfer journeys, a route explorer with actual GTFS
shapes, timetable statistics, and historical ticket-demand analytics for
20 matched routes. The previous schedule-based release remains separate.

| Area | Current outcome |
|---|---|
| Static transit | Supplied archive and read-only database verified, with 2,574 imported routes. |
| Historical demand | Manifest and schema validation, audited route mapping, paginated coverage, route-day profiles and responsive analytics live in the source. |
| Full-network demand | Custom export and crosswalk supported. Full export and authorized source observations were unavailable. |
| Segment occupancy | Unavailable pending verified vehicle-level passenger observations, trip assignment and capacity. |
| Live vehicle positions | Authorized GTFS-Realtime adapter implemented. Disabled by default. A provider key and release authorization are needed for an end-to-end live run. |
| Deployment | Compose and Caddy configuration validate. The workspace filled during the clean image build. The updated backend ran inside the previous container against the original read-only volume, with the newly built frontend. Public deployment remains pending. |
| CI | Repository workflow definition and local verification script added. Hosted execution requires the workflow to be accepted on GitHub. |

[Fresh test report](FINAL_TEST_REPORT.md) · [Open issues](FINAL_ISSUE_REGISTER.md) ·
[Deployment guide](DEPLOYMENT_GUIDE.md)

## Journey planner update

The current source includes stable itinerary deduplication, Delhi-clock
filtering, explicit historical timetable mode, validated transfer minimums,
and more detailed journey cards. The explorer still renders verified route
geometry when base tiles are unreachable. The analytics page adds dated
weekday and weekend timetable counts. The original citywide timetable and
20-route historical export were used for verification.

Readiness remains **local demonstration ready**. A fresh Docker Desktop
build and restart on the user's Windows PC and an end-to-end authorized live
feed run remain pending. [Latest end-to-end test evidence](FINAL_TEST_REPORT.md)
