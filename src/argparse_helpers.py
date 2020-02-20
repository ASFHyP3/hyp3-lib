import argparse
import os

# Throw if not exist:
def file_exists(path):
	if os.path.isfile(path):
		return path
	raise argparse.ArgumentTypeError("\n   -> File not found: {0}.".format(path))

def dir_exists(path):
	if os.path.isdir(path):
		return path
	raise argparse.ArgumentTypeError("\n   -> Directory not found: {0}.".format(path))

# Create if not exist:
def dir_exists_create(path):
	# Check if something is there already:
	if os.path.exists(path):
		if os.path.isdir(path):
			return path
		else:
			raise argparse.ArgumentTypeError("\n   -> Cannot create Directory, file has same name: {0}".format(path))
	# Try to create it:
	else:
		os.makedirs(path)
		return dir_exists(path)