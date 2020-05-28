import pytest

from hyp3lib import GranuleError, metadata


def test_add_esa_citation(tmp_path):
    granule = 'S1B_IW_GRDH_1SDV_20191005T151525_20191005T151554_018342_0228D3_656F'

    metadata.add_esa_citation(granule, tmp_path)

    assert (tmp_path / 'ESA_citation.txt').is_file()


def test_add_esa_citation_bad_granule_type(tmp_path):
    granule = 'boogers'

    with pytest.raises(GranuleError) as execinfo:
        metadata.add_esa_citation(granule, tmp_path)

    assert 'ESA citation only valid for S1 granules' in str(execinfo.value)


def test_add_esa_citation_bad_granule_time(tmp_path):
    granule = 'S1B_IW_GRDH_1SDV_boogers'

    with pytest.raises(GranuleError) as execinfo:
        metadata.add_esa_citation(granule, tmp_path)

    print(execinfo.value)

    assert 'Unable to determine acquisition year' in str(execinfo.value)
