import argparse
import os
import imageio
import shutil, glob
import subprocess
from skimage import img_as_ubyte

from argparse_helpers import file_exists, dir_exists_create
from asf_time_series import getNetcdfGranule
from time_series2geotiff import time_series2geotiff
# https://stackoverflow.com/questions/41228209/making-gif-from-images-using-imageio-in-python

def tiffListToNcFile(tiff_list, output, fps=2):
	tiff_stream_list = []
	for tiff in tiff_list:
		tiff = imageio.imread(tiff)
		tiff_stream_list.append(tiff)

	# Create the GIF:
	imageio.mimsave(output, tiff_stream_list, fps=fps)
	#Normalize the new GIF:
	subprocess.run(["convert", output,"-normalize", output])

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Creates a GIF, from a netCDF")
	parser.add_argument('-o','--output', action="store", metavar="<output gif>", default='timeseries.gif',
		help="Where to save the gif. Default=timeseries.gif (Both path/name supported).")
	parser.add_argument('-f', '--fps', action="store", type=int, default=2,
		help="FPS of generated gif. Default=2.")
	# You can only use exactly one of these:
	file_handler = parser.add_mutually_exclusive_group(required=True)
	file_handler.add_argument('-n', '--ncFile', action="store", type=file_exists,
		help="Path to the netCDF file.")
	file_handler.add_argument('-t', '--tiffDir', action="store", type=dir_exists_create,
		help="Path to the directory containing all the .tif files")
	
	args = parser.parse_args()

	if args.ncFile != None:
		created_tiffs = True
		# This dir will get wipped at the end. Make sure it's safe to do so:
		tmp_dir = "temp_tiffs"
		if os.path.isdir(tmp_dir) and len(os.listdir(tmp_dir)) != 0:
			print("Directory not empty! Quitting to avoid deleting work.\n   Directory: '{0}'.".format(tmp_dir))
			exit(-1)
		tiff_list = time_series2geotiff(args.ncFile, tmp_dir)

	elif args.tiffDir != None:
		created_tiffs = False # For if you need to delete them after:
		pattern = os.path.join(args.tiffDir, '*.tif')
		tiff_list = glob.glob(pattern)
		if len(tiff_list) == 0:
			print("No tiff's found! Looked for files matching: '{0}'.".format(pattern))
			exit(-1)

	tiffListToNcFile(tiff_list, args.output, fps=args.fps)

	if created_tiffs:
		shutil.rmtree(tmp_dir)