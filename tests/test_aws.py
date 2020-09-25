import pytest
from botocore.stub import ANY, Stubber

from hyp3lib import aws


@pytest.fixture(autouse=True)
def s3_stubber():
    with Stubber(aws.S3_CLIENT) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


def test_get_tag_set():
    assert aws.get_tag_set('foo.zip') == {'TagSet': [{'Key': 'file_type', 'Value': 'product'}]}
    assert aws.get_tag_set('foo.png') == {'TagSet': [{'Key': 'file_type', 'Value': 'amp-browse'}]}
    assert aws.get_tag_set('foo_thumb.png') == {'TagSet': [{'Key': 'file_type', 'Value': 'amp-thumbnail'}]}
    assert aws.get_tag_set('foo_rgb.png') == {'TagSet': [{'Key': 'file_type', 'Value': 'rgb-browse'}]}
    assert aws.get_tag_set('foo_rgb_thumb.png') == {'TagSet': [{'Key': 'file_type', 'Value': 'rgb-thumbnail'}]}
    assert aws.get_tag_set('foo.txt') == {'TagSet': [{'Key': 'file_type', 'Value': 'product'}]}


def test_get_content_type():
    assert aws.get_content_type('foo') == 'application/octet-stream'
    assert aws.get_content_type('foo.asfd') == 'application/octet-stream'
    assert aws.get_content_type('foo.txt') == 'text/plain'
    assert aws.get_content_type('foo.zip') == 'application/zip'
    assert aws.get_content_type('foo/bar.png') == 'image/png'


def test_upload_file_to_s3(tmp_path, s3_stubber):
    expected_params = {
        'Body': ANY,
        'Bucket': 'myBucket',
        'Key': 'myFile.zip',
        'ContentType': 'application/zip',
    }
    tag_params = {
        'Bucket': 'myBucket',
        'Key': 'myFile.zip',
        'Tagging': {
            'TagSet': [
                {'Key': 'file_type', 'Value': 'product'}
            ]
        }
    }
    s3_stubber.add_response(method='put_object', expected_params=expected_params, service_response={})
    s3_stubber.add_response(method='put_object_tagging', expected_params=tag_params, service_response={})

    file_to_upload = tmp_path / 'myFile.zip'
    file_to_upload.touch()
    aws.upload_file_to_s3(file_to_upload, 'myBucket')


def test_upload_file_to_s3_with_prefix(tmp_path, s3_stubber):
    expected_params = {
        'Body': ANY,
        'Bucket': 'myBucket',
        'Key': 'myPrefix/myFile.txt',
        'ContentType': 'text/plain',
    }
    tag_params = {
        'Bucket': 'myBucket',
        'Key': 'myPrefix/myFile.txt',
        'Tagging': {
            'TagSet': [
                {'Key': 'file_type', 'Value': 'product'}
            ]
        }
    }
    s3_stubber.add_response(method='put_object', expected_params=expected_params, service_response={})
    s3_stubber.add_response(method='put_object_tagging', expected_params=tag_params, service_response={})
    file_to_upload = tmp_path / 'myFile.txt'
    file_to_upload.touch()
    aws.upload_file_to_s3(file_to_upload, 'myBucket', 'myPrefix')
