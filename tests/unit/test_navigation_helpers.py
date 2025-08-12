from openchronicle.domain.services.timeline.navigation.navigation_manager import NavigationManager


def test_format_display_time_happy():
    nm = NavigationManager("s-1")
    assert nm._format_display_time("2025-08-10T12:00:00Z").startswith("2025-")


def test_format_display_time_invalid():
    nm = NavigationManager("s-1")
    assert nm._format_display_time("not-a-time") == "not-a-time"
