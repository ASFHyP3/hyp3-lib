from hyp3lib.getSubSwath import get_bounding_box_file


def test_get_bounding_box_file(safe_data):
    expected = (39.22924837602602, 36.96964287499973, -111.0340780928982, -114.513182762547)
    assert get_bounding_box_file(safe_data) == expected
