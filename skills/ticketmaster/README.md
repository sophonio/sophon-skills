# Ticketmaster Skill

Ticketmaster Discovery API integration for Sophon — search live events, look up event details
(including on-sale dates and price ranges), find performers and their upcoming shows, search
venues, browse the segment/genre taxonomy, and get typeahead suggestions.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `ticketmaster.search_events` | None | Search events by keyword, city, country, date window, and classification |
| `ticketmaster.get_event` | None | Full event detail incl. on-sale dates, venue, price ranges, seatmap |
| `ticketmaster.search_attractions` | None | Search performers/artists/teams by keyword |
| `ticketmaster.get_attraction_events` | None | Upcoming events for a specific performer (attraction id) |
| `ticketmaster.search_venues` | None | Search venues by keyword (id, name, city, country) |
| `ticketmaster.list_classifications` | None | Segment/genre taxonomy (Music, Sports, ...) |
| `ticketmaster.suggest` | None | Typeahead suggestions for a partial keyword |

## Setup

1. Go to https://developer.ticketmaster.com/ and sign up for a free developer account
2. Create an app in **My Apps** — every new app is instantly granted Discovery API access
3. Copy the app's **Consumer Key** (this is the API key)
4. In the Sophon Dashboard, go to **Settings > Connections**
5. Click **Connect** on the Ticketmaster card, paste the Consumer Key, and test the connection

## Usage Examples

**Search events:**
> "Find rock concerts in Boston next month on Ticketmaster"

**Event details:**
> "When do tickets go on sale for event G5vYZ4x1sVo-1, and what are the price ranges?"

**Performer lookup:**
> "Search Ticketmaster for Coldplay and list their upcoming shows"

**Venues:**
> "Find Madison Square Garden on Ticketmaster"

**Typeahead:**
> "What does Ticketmaster suggest for 'tayl'?"

## Requirements

- Free Ticketmaster developer account with a Consumer Key (instant self-serve at developer.ticketmaster.com)
- Default quota is limited (roughly 5000 calls/day at 5 requests/second) — the skill throttles politely; keep usage to about 2 requests/second
- Deep paging is capped: `size * (page + 1)` must stay at or under 1000 results per query
- Coverage is biased toward Ticketmaster-ticketed events — events sold through other ticketers may be missing

## Attribution & Trademarks

Event, attraction, and venue data is provided by the **Ticketmaster Discovery API**. Use of the
API is subject to the [Ticketmaster API Terms of Use](https://developer.ticketmaster.com/support/terms-of-use/):
access to the API may not be resold or redistributed, and responses should only be cached
briefly/reasonably (event availability and on-sale data change frequently).

Ticketmaster is a registered trademark of Ticketmaster LLC / Live Nation Entertainment, Inc.
This skill is an independent integration developed by Buildersoft LLC and is not affiliated
with, endorsed by, certified by, or sponsored by Ticketmaster or Live Nation Entertainment.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
