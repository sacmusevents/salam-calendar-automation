# Salam Center Calendar Automation

Automated scraper for [SALAM Islamic Center](https://salamcenter.org) events. Fetches events from the RSS feed and generates an iCalendar (ICS) file that can be imported into Google Calendar, Apple Calendar, or any other calendar application.

## Features

- ✅ Parses events from Salam Center RSS feed
- ✅ Generates iCalendar (ICS) format
- ✅ **Incremental scraping**: Only fetches new events, stops at existing ones
- ✅ **Smart deduplication**: Prevents duplicate calendar entries
- ✅ **Calendar merging**: Preserves historical events while adding new ones
- ✅ Automatic updates via GitHub Actions (every 6 hours)
- ✅ Comprehensive test suite

## Quick Start

### Local Setup

```bash
# Clone the repository
git clone https://github.com/sacmusevents/salam-calendar-automation.git
cd salam-calendar-automation

# Install dependencies
pip install -r requirements.txt

# Run the scraper
python3 scrape_salam_events.py
```

This generates `salam_events.ics` with all upcoming events.

### Import into Google Calendar

1. Go to [Google Calendar](https://calendar.google.com)
2. Click the **"+"** button next to "Other calendars"
3. Select **"From URL"**
4. Paste the public URL to the raw ICS file
5. Click **"Subscribe"**

### Import into Apple Calendar

1. Open Calendar app
2. Go to **File** → **New Calendar Subscription**
3. Paste the ICS file URL
4. Click **Create**

## How It Works

### Data Source

The scraper fetches events from:
- **RSS Feed**: `https://salamcenter.org/events/feed/`
- **Source**: Salam Center's WordPress event calendar

### Incremental Scraping

The scraper is designed for efficiency:

1. **On first run**: Downloads all events from the RSS feed
2. **On subsequent runs**:
   - Loads existing events from `salam_events.ics`
   - Checks each new RSS item against existing events
   - **Stops scraping** when it encounters an event that already exists
   - Only adds truly new events to the calendar

### Calendar Merging

- **Preserves** all historical events
- **Adds** only new events
- **Prevents** duplicate entries
- **Reports** statistics (existing + new + total events)

## Project Structure

```
salam-calendar-automation/
├── scrape_salam_events.py      # Main scraper script
├── test_salam_scraper.py       # Comprehensive test suite
├── requirements.txt             # Python dependencies
├── salam_events.ics            # Generated calendar (git-tracked)
├── README.md                   # This file
└── .github/
    └── workflows/
        └── sync-calendar.yml   # GitHub Actions automation
```

## Testing

Run the comprehensive test suite:

```bash
python3 test_salam_scraper.py
```

Tests cover:
- Scraper initialization
- HTML tag stripping
- RFC 2822 date parsing
- Incremental scraping with existing events
- ICS calendar generation
- Calendar merging (new + existing)

## GitHub Actions (Automated Updates)

The scraper runs automatically every 6 hours via GitHub Actions:

- ✅ Runs integration tests
- ✅ Fetches latest events
- ✅ Merges with existing calendar
- ✅ Commits changes to repository
- ✅ Generates run summary

View recent runs: [Actions](https://github.com/sacmusevents/salam-calendar-automation/actions)

## API & Feed References

### Salam Center

- **Website**: https://salamcenter.org
- **Events Page**: https://salamcenter.org/events/
- **RSS Feed**: https://salamcenter.org/events/feed/
- **CMS**: WordPress with Modern Events Calendar plugin

### Event Details Available

- Event title
- Date and time
- Description (from content)
- Event link
- Location (extracted from description)

## Requirements

- Python 3.8+
- `requests` - HTTP requests
- `feedparser` - RSS/Atom feed parsing
- `ics` - iCalendar format generation
- `pytz` - Timezone handling

See `requirements.txt` for exact versions.

## Development

### Running Locally

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run scraper with verbose output
python3 scrape_salam_events.py

# Run tests
python3 test_salam_scraper.py

# Test incremental updates (run twice)
python3 scrape_salam_events.py
python3 scrape_salam_events.py  # Should find 0 new events
```

### Debugging

The scraper provides detailed output:
- Event parsing results (✓ NEW, ≡ Existing, ✗ Skipped)
- Calendar merge statistics
- File generation timestamp

### Architecture

**SalamEventsScraper class** handles:
- RSS feed fetching and parsing
- Event extraction and validation
- Date/time parsing (RFC 2822 format)
- Event deduplication
- iCalendar generation
- File I/O and merging

**Key Methods**:
- `scrape_events()` - Fetch and process RSS feed
- `extract_event_details()` - Parse individual events
- `_event_exists()` - Check for duplicates
- `generate_ics()` - Create/merge ICS file

## Troubleshooting

### "No events found"

- Check RSS feed is accessible: https://salamcenter.org/events/feed/
- Verify internet connection
- Check scraper output for parsing errors

### Duplicate events in calendar

- Not possible with current implementation
- Deduplication uses title + start datetime
- Each event only appears once in merged calendar

### Wrong times/timezones

- Events are in Pacific Time (PST/PDT)
- Check your calendar app timezone settings
- Calendar exports in UTC (Z format) but displays in local time

## Contributing

To improve the scraper:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is provided as-is for community use.

## Contact

For issues or questions about the scraper:
- File an issue on GitHub
- Check existing issues first

For questions about Salam Center events:
- Visit https://salamcenter.org
- Contact Salam Islamic Center directly

---

**Generated**: December 2025
**Last Updated**: Check GitHub commits for latest changes
