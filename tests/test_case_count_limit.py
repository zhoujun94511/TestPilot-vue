from services.case_count import MAX_CASES_PER_REQUIREMENT, clamp_cases_per_requirement


def test_case_count_clamps_to_ten():
    assert clamp_cases_per_requirement(50) == MAX_CASES_PER_REQUIREMENT
    assert clamp_cases_per_requirement(10) == 10
    assert clamp_cases_per_requirement(1) == 1


def test_case_count_rejects_empty_and_zero():
    assert clamp_cases_per_requirement(None, 5) == 5
    assert clamp_cases_per_requirement("x", 3) == 3
    assert clamp_cases_per_requirement(0, 3) == 1
    assert clamp_cases_per_requirement(-4, 3) == 1
