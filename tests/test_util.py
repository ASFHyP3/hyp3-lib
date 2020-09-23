from hyp3lib import util


def test_string_is_true():
    assert util.string_is_true('true') is True
    assert util.string_is_true('tRuE') is True
    assert util.string_is_true('True') is True
    assert util.string_is_true('TRUE') is True
    assert util.string_is_true('tuue') is False
    assert util.string_is_true('boogers') is False
    assert util.string_is_true('false') is False
