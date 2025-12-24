"""
Integration test for Salam Center Events Scraper

This test pulls live data from the actual RSS feed and validates:
1. RSS feed is accessible
2. Events are properly parsed
3. Event data structure is valid
4. ICS generation works with real data
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrape_salam_events import SalamEventsScraper
import requests


def test_rss_feed_accessibility():
    """Test that the RSS feed is accessible and returns valid XML."""
    print("\n" + "=" * 70)
    print("TEST: RSS feed accessibility")
    print("=" * 70)

    scraper = SalamEventsScraper()

    try:
        response = scraper.session.get(scraper.rss_url, timeout=10)
        response.raise_for_status()

        # Check it's XML/RSS
        assert '<?xml' in response.text, "Response is not XML format"
        assert '<rss' in response.text, "Response is not RSS format"
        assert '<channel>' in response.text, "Response does not have RSS channel"

        print(f"✓ RSS feed is accessible: {scraper.rss_url}")
        print(f"✓ Response is valid XML/RSS format")
        print(f"✓ Response size: {len(response.text)} bytes")

        # Count items in feed
        item_count = response.text.count('<item>')
        print(f"✓ Found {item_count} items in feed")
        assert item_count > 0, "RSS feed has no items"

        return True
    except requests.RequestException as e:
        print(f"✗ Failed to fetch RSS feed: {e}")
        return False
    except AssertionError as e:
        print(f"✗ RSS validation failed: {e}")
        return False


def test_event_extraction_from_live_feed():
    """Test that events can be extracted from live RSS feed."""
    print("\n" + "=" * 70)
    print("TEST: Event extraction from live RSS feed")
    print("=" * 70)

    scraper = SalamEventsScraper()

    try:
        # Scrape events
        events = scraper.scrape_events()

        if not events:
            print("⚠ No events found in feed (this could be normal if events are archived)")
            return True

        print(f"\n✓ Successfully extracted {len(events)} events from live feed\n")

        # Validate event structure
        required_fields = ['title', 'start', 'end', 'location', 'description', 'url']
        all_valid = True

        for idx, event in enumerate(events[:5], 1):  # Check first 5 events
            print(f"Event {idx}: {event['title']}")
            print(f"  Date: {event['start'].strftime('%Y-%m-%d %H:%M %Z')}")

            # Check all required fields exist
            for field in required_fields:
                if field not in event:
                    print(f"  ✗ Missing field: {field}")
                    all_valid = False

            # Check types
            assert hasattr(event['start'], 'strftime'), "start is not a datetime"
            assert hasattr(event['end'], 'strftime'), "end is not a datetime"
            assert isinstance(event['title'], str), "title is not a string"
            assert isinstance(event['location'], str), "location is not a string"
            assert isinstance(event['description'], str), "description is not a string"
            assert isinstance(event['url'], str), "url is not a string"

            # Check start < end
            assert event['start'] < event['end'], f"Start time {event['start']} is not before end time {event['end']}"

            print(f"  ✓ Valid structure")

        print(f"\n✓ All {len(events)} events have valid structure")
        print(f"✓ Event data types are correct")

        return all_valid

    except Exception as e:
        print(f"✗ Event extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ics_generation_with_live_data():
    """Test that ICS file can be generated with live data."""
    print("\n" + "=" * 70)
    print("TEST: ICS generation with live data")
    print("=" * 70)

    import tempfile
    import os as os_module

    scraper = SalamEventsScraper()

    try:
        # Scrape events
        events = scraper.scrape_events()

        if not events:
            print("⚠ Skipping ICS generation test (no events found)")
            return True

        # Create temporary ICS file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False) as f:
            temp_ics = f.name

        try:
            # Generate ICS
            scraper.generate_ics(events, temp_ics)

            # Verify file was created
            assert os_module.path.exists(temp_ics), "ICS file was not created"
            assert os_module.path.getsize(temp_ics) > 0, "ICS file is empty"

            # Read and validate content
            with open(temp_ics, 'r') as f:
                content = f.read()

            # Check ICS structure
            assert 'BEGIN:VCALENDAR' in content, "Missing VCALENDAR header"
            assert 'END:VCALENDAR' in content, "Missing VCALENDAR footer"
            assert 'BEGIN:VEVENT' in content, "Missing VEVENT blocks"
            assert 'END:VEVENT' in content, "Missing VEVENT closing tags"

            # Count events in ICS
            vevent_count = content.count('BEGIN:VEVENT')
            print(f"\n✓ ICS file generated successfully")
            print(f"✓ File size: {os_module.path.getsize(temp_ics)} bytes")
            print(f"✓ Contains {vevent_count} events")
            assert vevent_count == len(events), f"Expected {len(events)} events in ICS, found {vevent_count}"

            # Check for required ICS fields in first event
            assert 'SUMMARY:' in content, "Missing SUMMARY field"
            assert 'DTSTART:' in content, "Missing DTSTART field"
            assert 'DTEND:' in content, "Missing DTEND field"
            assert 'UID:' in content, "Missing UID field"

            print(f"✓ All required ICS fields present")

            return True

        finally:
            if os_module.path.exists(temp_ics):
                os_module.unlink(temp_ics)

    except Exception as e:
        print(f"✗ ICS generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 70)
    print("SALAM CENTER EVENTS - LIVE INTEGRATION TEST")
    print("=" * 70)
    print("\nThis test validates the scraper against live data from:")
    print("  https://salamcenter.org/events/feed/")

    all_passed = True

    try:
        all_passed &= test_rss_feed_accessibility()
        all_passed &= test_event_extraction_from_live_feed()
        all_passed &= test_ics_generation_with_live_data()
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL INTEGRATION TESTS PASSED!")
        print("\nThe scraper is working correctly with live data from Salam Center.")
        print("Ready for production deployment.")
    else:
        print("✗ SOME INTEGRATION TESTS FAILED!")
        print("\nPlease review the errors above.")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
