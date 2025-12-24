#!/usr/bin/env python3
"""
Salam Center Events Scraper
Scrapes events from salamcenter.org RSS feed and generates an ICS calendar file
"""

import requests
import feedparser
from datetime import datetime, timedelta
from ics import Calendar, Event
import pytz
import re
import hashlib
from typing import List, Dict, Optional
import sys
from html.parser import HTMLParser


class MLStripper(HTMLParser):
    """Helper class to strip HTML tags"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return ''.join(self.text)


def strip_html(html: str) -> str:
    """Remove HTML tags from string"""
    if not html:
        return ""
    s = MLStripper()
    s.feed(html)
    return s.get_data()


class SalamEventsScraper:
    def __init__(self, ics_file: str = "salam_events.ics"):
        self.rss_url = "https://salamcenter.org/events/feed/"
        self.timezone = pytz.timezone('America/Los_Angeles')
        self.ics_file = ics_file
        self.existing_events = self._load_existing_events()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _load_existing_events(self) -> Dict[str, str]:
        """Load existing event UIDs and summaries from ICS file for deduplication.

        Returns a dict mapping "title|DTSTART" to True for quick lookup.
        """
        existing = {}
        try:
            with open(self.ics_file, 'r') as f:
                content = f.read()

            # Parse ICS file for events
            in_event = False
            event_summary = ""
            event_dtstart = ""

            for line in content.split('\n'):
                if line.startswith('BEGIN:VEVENT'):
                    in_event = True
                    event_summary = ""
                    event_dtstart = ""
                elif line.startswith('END:VEVENT'):
                    if event_summary and event_dtstart:
                        # Create a unique identifier: title + start date
                        key = f"{event_summary}|{event_dtstart}"
                        existing[key] = True
                    in_event = False
                elif in_event:
                    if line.startswith('SUMMARY:'):
                        event_summary = line[8:]  # Skip "SUMMARY:"
                    elif line.startswith('DTSTART:'):
                        event_dtstart = line[8:]  # Skip "DTSTART:"

            print(f"✓ Loaded {len(existing)} existing events from {self.ics_file}")
            return existing
        except FileNotFoundError:
            print(f"⚠ No existing ICS file found ({self.ics_file}), will create new calendar")
            return {}
        except Exception as e:
            print(f"⚠ Error reading existing ICS file: {e}")
            return {}

    def _event_exists(self, title: str, start: datetime) -> bool:
        """Check if an event already exists in the calendar."""
        start_str = start.astimezone(pytz.utc).strftime('%Y%m%dT%H%M%SZ')
        key = f"{title}|{start_str}"
        return key in self.existing_events

    def parse_event_time(self, pub_date_str: str) -> Optional[datetime]:
        """Parse RSS pubDate format to datetime.

        Format: 'Thu, 25 Dec 2025 17:00:00 -0800'
        """
        try:
            # Parse RFC 2822 format (standard RSS pubDate)
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date_str)
            # Convert to timezone-aware datetime in Pacific time
            return dt.astimezone(self.timezone)
        except Exception as e:
            print(f"Warning: Could not parse date '{pub_date_str}': {e}")
            return None

    def extract_event_details(self, item: dict) -> Optional[Dict]:
        """Extract event details from RSS item.

        Handles both standard pubDate and Modern Events Calendar (MEC) custom fields.
        """
        try:
            title = item.get('title', '')
            if not title:
                return None

            # Try to get date from standard pubDate first
            pub_date_str = item.get('published', '')
            start = None

            if pub_date_str:
                start = self.parse_event_time(pub_date_str)

            # If no pubDate, try MEC custom fields
            if not start:
                # Check for mec:startDate (format: 2026-01-09)
                mec_start = item.get('mec_startdate', '')
                if mec_start:
                    try:
                        # Parse YYYY-MM-DD format
                        dt = datetime.strptime(mec_start, '%Y-%m-%d')
                        # Set default time to 9:00 AM for all-day events
                        dt = dt.replace(hour=9, minute=0, second=0)
                        start = self.timezone.localize(dt)
                    except Exception as e:
                        print(f"  ✗ Skipped (could not parse MEC date): {title} - {e}")
                        return None

            if not start:
                print(f"  ✗ Skipped (no date found): {title}")
                return None

            # Default to 2-hour event, but check for MEC end date
            end = start + timedelta(hours=2)

            # If we used MEC startDate, also check for MEC endDate
            mec_end = item.get('mec_enddate', '')
            if mec_end:
                try:
                    # Parse YYYY-MM-DD format
                    end_dt = datetime.strptime(mec_end, '%Y-%m-%d')
                    # Set time to 5:00 PM for end of all-day events
                    end_dt = end_dt.replace(hour=17, minute=0, second=0)
                    end = self.timezone.localize(end_dt)
                except Exception:
                    pass  # Keep the default 2-hour duration

            # Extract content/description
            content = item.get('content', [{}])[0].get('value', '') if item.get('content') else ''
            description = strip_html(content) if content else ''

            # Get link
            link = item.get('link', '')

            # Extract location - check MEC field first, then description
            location = item.get('mec_location', '')  # MEC custom field

            # If no MEC location, try to extract from description
            if not location:
                location_match = re.search(r'Location:?\s*([^\n]+)', description, re.IGNORECASE)
                if location_match:
                    location = location_match.group(1).strip()

            return {
                'title': title,
                'start': start,
                'end': end,
                'location': location,
                'description': description,
                'url': link
            }
        except Exception as e:
            print(f"Error extracting event details: {e}")
            return None

    def scrape_events(self) -> List[Dict]:
        """Scrape events from Salam Center RSS feed."""
        print("=" * 60)
        print("Salam Center Events Scraper")
        print("=" * 60)
        print()

        all_events = []
        stop_scraping = False

        try:
            print(f"Fetching RSS feed: {self.rss_url}")
            response = self.session.get(self.rss_url, timeout=10)
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if not feed.entries:
                print("No events found in feed")
                return all_events

            print(f"Found {len(feed.entries)} items in feed\n")

            # Process each item
            for idx, item in enumerate(feed.entries, 1):
                if stop_scraping:
                    print(f"\n✓ Reached existing events, stopping scrape")
                    break

                event_data = self.extract_event_details(item)
                if not event_data:
                    continue

                title = event_data['title']
                start = event_data['start']

                # Check if event already exists
                if self._event_exists(title, start):
                    print(f"  ≡ Existing: {title}")
                    stop_scraping = True
                else:
                    all_events.append(event_data)
                    print(f"  ✓ NEW: {title} - {start.strftime('%Y-%m-%d %H:%M')}")

            print(f"\nTotal new events scraped: {len(all_events)}")
            return all_events

        except Exception as e:
            print(f"Error scraping events: {e}")
            import traceback
            traceback.print_exc()
            return all_events

    def generate_ics(self, events: List[Dict], filename: str = "salam_events.ics"):
        """Generate ICS calendar file from events.

        Merges new events with existing ones in the calendar file.
        """
        # First, load existing events from the file if it exists
        existing_event_text = ""
        existing_count = 0
        try:
            with open(filename, 'r') as f:
                content = f.read()

            # Extract all existing VEVENT blocks
            in_event = False
            current_event_lines = []

            for line in content.split('\n'):
                if line.startswith('BEGIN:VEVENT'):
                    in_event = True
                    current_event_lines = [line]
                elif line.startswith('END:VEVENT'):
                    in_event = False
                    current_event_lines.append(line)
                    existing_event_text += '\n'.join(current_event_lines) + '\n'
                    existing_count += 1
                    current_event_lines = []
                elif in_event:
                    current_event_lines.append(line)

            print(f"✓ Preserved {existing_count} existing events from {filename}")
        except FileNotFoundError:
            print(f"⚠ No existing calendar file found, creating new one")
        except Exception as e:
            print(f"⚠ Could not load existing events: {e}")

        # Now create new events
        calendar = Calendar()
        new_count = 0
        for event_data in events:
            try:
                event = Event()
                event.name = event_data['title']
                event.begin = event_data['start']
                event.end = event_data['end']
                event.location = event_data['location']

                # Validate times
                if not event.begin or not event.end:
                    print(f"Warning: Event '{event_data['title']}' has missing begin or end time")
                    continue

                if event.end < event.begin:
                    print(f"Warning: Event '{event_data['title']}' has end before begin, skipping")
                    continue

                # Combine description and URL
                description_parts = []
                if event_data['description']:
                    description_parts.append(event_data['description'])
                if event_data['url']:
                    description_parts.append(f"\n\nMore info: {event_data['url']}")

                event.description = '\n'.join(description_parts)

                # Create unique identifier
                title_hash = hashlib.md5(event_data['title'].encode()).hexdigest()[:8]
                event.uid = f"{event_data['start'].strftime('%Y%m%d%H%M%S')}-{title_hash}"

                calendar.events.add(event)
                new_count += 1
            except Exception as e:
                print(f"Error creating ICS event for '{event_data['title']}': {e}")
                continue

        # Write calendar with new events first, then existing events
        with open(filename, 'w') as f:
            # Start with calendar header
            f.write('BEGIN:VCALENDAR\n')
            f.write('VERSION:2.0\n')
            f.write('PRODID:ics.py - http://git.io/lLljaA\n')
            f.write(f'COMMENT:Generated at {datetime.now().isoformat()}\n')

            # Write new events first (they're the most recent)
            calendar_lines = calendar.serialize().split('\n')
            for line in calendar_lines[3:-1]:  # Start from line 3 (after header), skip last line
                if line.strip() and not line.startswith('VERSION:') and not line.startswith('PRODID:'):
                    f.write(line + '\n')

            # Write existing events
            if existing_event_text:
                f.write(existing_event_text)

            # End calendar
            f.write('END:VCALENDAR\n')

        total_events = existing_count + new_count
        print(f"\n✓ Generated calendar file: {filename}")
        print(f"  Existing events: {existing_count}")
        print(f"  New events added: {new_count}")
        print(f"  Total events: {total_events}")
        print(f"  Generated: {datetime.now().isoformat()}")

        return filename


def main():
    print()
    scraper = SalamEventsScraper()

    # Scrape all events from RSS feed
    events = scraper.scrape_events()

    # For incremental updates, generate ICS even if no NEW events found
    if not events and not scraper.existing_events:
        print("\n⚠ No events found and no existing calendar!")
        sys.exit(1)

    # Generate ICS file (merges new events with existing ones)
    ics_file = scraper.generate_ics(events, "salam_events.ics")

    print("\n" + "=" * 60)
    print("✓ Scraping complete!")
    print("=" * 60)
    print(f"\nTo import into Google Calendar:")
    print("1. Go to Google Calendar")
    print("2. Click '+' next to 'Other calendars'")
    print("3. Select 'From URL'")
    print("4. Paste the public URL of salam_events.ics")
    print()


if __name__ == "__main__":
    main()
