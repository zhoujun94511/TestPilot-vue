"""用例类别、优先级筛选要覆盖库里的原文。"""

from services.case_field_filters import case_category_values, case_priority_values


def test_functional_filter_matches_chinese_label():
    values = case_category_values('functional')
    assert '功能测试' in values
    assert 'functional' in values


def test_chinese_category_matches_the_same_group():
    assert case_category_values('接口测试') == case_category_values('integration')
    assert '自动化测试' in case_category_values('regression')


def test_unknown_category_stays_exact():
    assert case_category_values('可访问性测试') == ['可访问性测试']
    assert case_category_values('') == []


def test_priority_synonyms():
    assert 'high' in case_priority_values('P1')
    assert case_priority_values('P4')[0] == 'P4'
