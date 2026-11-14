from patchwise.core.risk_engine import calculate_priority


def test_calculate_priority_uses_cvss_and_kev():
    finding = {
        "cvss_score": 9.8,
        "is_kev": True,
        "fix_available": True,
        "direct_dependency": True,
    }

    level, label = calculate_priority(finding)

    assert level == 1
    assert label == "Critical"


def test_calculate_priority_low_for_minor_issue():
    finding = {
        "cvss_score": 2.5,
        "is_kev": False,
        "fix_available": False,
        "direct_dependency": False,
    }

    level, label = calculate_priority(finding)

    assert level == 4
    assert label == "Low"
