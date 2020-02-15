import argparse
import imageio
from asf_time_series import getNetcdfGranule

# https://stackoverflow.com/questions/41228209/making-gif-from-images-using-imageio-in-python

images = []
for image in image_list:
	path = os.path.join("cameron-test", image + "time_series.tif")
	images.append(imageio.imread(path))

def createGifFromNetcdf(ncFile):
	pass

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Creates a GIF, from a netCDF")
