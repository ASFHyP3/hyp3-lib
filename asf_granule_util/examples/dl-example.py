import asf_granule_util as gu


def download_granule():
    creds = {
        'username': USERNAME,
        'password': PASSWORD
    }

    gu.download(
        'S1A_IW_SLC__1SSV_20150829T123751_20150829T123821_007478_00A50D_C506',
        credentials=creds,
        directory='.',
        progess_bar=True
    )


if __name__ == "__main__":
    download_granule()
