"""
Test suite for Salam Center Events Scraper

Tests:
1. RSS feed parsing
2. Event extraction
3. Event deduplication with existing events
4. ICS calendar generation
5. Calendar merging (new + existing events)
"""

import sys
import os
import tempfile
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrape_salam_events import SalamEventsScraper


def test_scraper_initialization():
    """Test that scraper initializes properly."""
    print("\n" + "=" * 70)
    print("TEST: Scraper initialization")
    print("=" * 70)

    scraper = SalamEventsScraper()
    assert scraper.rss_url == "https://salamcenter.org/events/feed/"
    assert scraper.ics_file == "salam_events.ics"
    assert isinstance(scraper.existing_events, dict)
    print("✓ Scraper initialized correctly")
    return True


def test_html_stripping():
    """Test HTML stripping function."""
    print("\n" + "=" * 70)
    print("TEST: HTML tag stripping")
    print("=" * 70)

    from scrape_salam_events import strip_html

    html = "<p>This is <b>bold</b> text with <a href='#'>link</a></p>"
    result = strip_html(html)
    assert "This is" in result
    assert "bold" in result
    assert "<" not in result
    assert ">" not in result
    print(f"✓ HTML stripping works: '{result}'")
    return True


def test_time_parsing():
    """Test RFC 2822 date parsing."""
    print("\n" + "=" * 70)
    print("TEST: RFC 2822 date parsing")
    print("=" * 70)

    scraper = SalamEventsScraper()

    # Test case 1: Valid RFC 2822 date
    date_str = "Thu, 25 Dec 2025 17:00:00 -0800"
    result = scraper.parse_event_time(date_str)
    assert result is not None, "Failed to parse valid RFC 2822 date"
    print(f"✓ Parsed '{date_str}'")
    print(f"  Result: {result.strftime('%Y-%m-%d %H:%M %Z')}")

    # Test case 2: Another valid date
    date_str2 = "Fri, 26 Dec 2025 12:00:00 -0800"
    result2 = scraper.parse_event_time(date_str2)
    assert result2 is not None, "Failed to parse second RFC 2822 date"
    print(f"✓ Parsed '{date_str2}'")
    print(f"  Result: {result2.strftime('%Y-%m-%d %H:%M %Z')}")

    return True


def test_incremental_scraping():
    """Test that scraper recognizes existing events and stops."""
    print("\n" + "=" * 70)
    print("TEST: Incremental scraping with existing events")
    print("=" * 70)

    # Create a temporary ICS file with an existing event
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False)
    tz = pytz.timezone('America/Los_Angeles')
    existing_event_start = tz.localize(datetime(2025, 12, 26, 12, 0, 0))

    temp_file.write('BEGIN:VCALENDAR\n')
    temp_file.write('VERSION:2.0\n')
    temp_file.write('PRODID:ics.py - http://git.io/lLljaA\n')
    temp_file.write(f'COMMENT:Generated at {datetime.now().isoformat()}\n')
    temp_file.write('BEGIN:VEVENT\n')
    temp_file.write('SUMMARY:Arabic-Language Jumuah – جمعة باللغة العربية\n')
    temp_file.write(f'DTSTART:{existing_event_start.astimezone(pytz.utc).strftime("%Y%m%dT%H%M%SZ")}\n')
    temp_file.write('DTEND:20251226T130000Z\n')
    temp_file.write('UID:20251226120000-testuid\n')
    temp_file.write('END:VEVENT\n')
    temp_file.write('END:VCALENDAR\n')
    temp_file.close()

    try:
        # Create scraper with existing ICS
        scraper = SalamEventsScraper(ics_file=temp_file.name)
        assert len(scraper.existing_events) == 1, f"Expected 1 existing event, got {len(scraper.existing_events)}"
        print(f"✓ Loaded {len(scraper.existing_events)} existing event")

        # Check if the event is recognized as existing
        exists = scraper._event_exists(
            "Arabic-Language Jumuah – جمعة باللغة العربية",
            existing_event_start
        )
        assert exists, "Event should be recognized as existing"
        print("✓ Event correctly identified as existing")

        # Check a non-existing event
        new_event_start = tz.localize(datetime(2026, 1, 4, 10, 0, 0))
        not_exists = scraper._event_exists("Al-Misbaah Food Drive", new_event_start)
        assert not not_exists, "Event should NOT be recognized as existing"
        print("✓ New event correctly identified as not existing")

        return True
    finally:
        os.unlink(temp_file.name)


def test_calendar_generation():
    """Test ICS calendar generation."""
    print("\n" + "=" * 70)
    print("TEST: ICS calendar generation")
    print("=" * 70)

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False)
    temp_file.close()

    try:
        scraper = SalamEventsScraper(ics_file=temp_file.name)
        tz = pytz.timezone('America/Los_Angeles')

        # Create test events
        test_events = [
            {
                'title': 'Test Event 1',
                'start': tz.localize(datetime(2025, 12, 25, 17, 0, 0)),
                'end': tz.localize(datetime(2025, 12, 25, 19, 0, 0)),
                'location': 'Test Location',
                'description': 'Test description',
                'url': 'https://example.com/event1'
            },
            {
                'title': 'Test Event 2',
                'start': tz.localize(datetime(2025, 12, 26, 12, 0, 0)),
                'end': tz.localize(datetime(2025, 12, 26, 14, 0, 0)),
                'location': 'Another Location',
                'description': 'Another description',
                'url': 'https://example.com/event2'
            }
        ]

        scraper.generate_ics(test_events, temp_file.name)

        # Verify the calendar was created
        with open(temp_file.name, 'r') as f:
            content = f.read()

        event_count = content.count('BEGIN:VEVENT')
        assert event_count == 2, f"Expected 2 events, found {event_count}"
        assert 'Test Event 1' in content, "Test Event 1 not found"
        assert 'Test Event 2' in content, "Test Event 2 not found"
        assert 'Test Location' in content, "Location not found"
        print(f"✓ Generated calendar with {event_count} events")
        print("✓ Calendar contains all event details")

        return True
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


def test_calendar_merging():
    """Test that new and existing events are properly merged."""
    print("\n" + "=" * 70)
    print("TEST: Calendar merging (existing + new events)")
    print("=" * 70)

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False)
    tz = pytz.timezone('America/Los_Angeles')

    # Create initial ICS with 1 event
    temp_file.write('BEGIN:VCALENDAR\n')
    temp_file.write('VERSION:2.0\n')
    temp_file.write('PRODID:ics.py - http://git.io/lLljaA\n')
    temp_file.write(f'COMMENT:Generated at {datetime.now().isoformat()}\n')
    temp_file.write('BEGIN:VEVENT\n')
    temp_file.write('SUMMARY:Existing Event\n')
    temp_file.write('DTSTART:20251225T170000Z\n')
    temp_file.write('DTEND:20251225T190000Z\n')
    temp_file.write('UID:20251225170000-existing\n')
    temp_file.write('END:VEVENT\n')
    temp_file.write('END:VCALENDAR\n')
    temp_file.close()

    try:
        scraper = SalamEventsScraper(ics_file=temp_file.name)

        # Create new events
        new_events = [
            {
                'title': 'New Event 1',
                'start': tz.localize(datetime(2025, 12, 26, 12, 0, 0)),
                'end': tz.localize(datetime(2025, 12, 26, 14, 0, 0)),
                'location': 'Location 1',
                'description': 'Description 1',
                'url': ''
            },
            {
                'title': 'New Event 2',
                'start': tz.localize(datetime(2025, 12, 27, 10, 0, 0)),
                'end': tz.localize(datetime(2025, 12, 27, 12, 0, 0)),
                'location': 'Location 2',
                'description': 'Description 2',
                'url': ''
            }
        ]

        scraper.generate_ics(new_events, temp_file.name)

        # Verify merged calendar
        with open(temp_file.name, 'r') as f:
            content = f.read()

        event_count = content.count('BEGIN:VEVENT')
        assert event_count == 3, f"Expected 3 total events (1 existing + 2 new), found {event_count}"
        assert 'Existing Event' in content, "Existing event not found"
        assert 'New Event 1' in content, "New Event 1 not found"
        assert 'New Event 2' in content, "New Event 2 not found"
        print(f"✓ Merged calendar has {event_count} events (1 existing + 2 new)")
        print("✓ No duplicate events in merged calendar")

        return True
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


if __name__ == "__main__":
    all_passed = True

    try:
        all_passed &= test_scraper_initialization()
        all_passed &= test_html_stripping()
        all_passed &= test_time_parsing()
        all_passed &= test_incremental_scraping()
        all_passed &= test_calendar_generation()
        all_passed &= test_calendar_merging()
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        all_passed = False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ All tests PASSED!")
    else:
        print("✗ Some tests FAILED!")
    print("=" * 70 + "\n")

    sys.exit(0 if all_passed else 1)
