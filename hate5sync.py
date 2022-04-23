import glob
import os
import cv2
import librosa
import ffmpeg
import numpy as np
import easygui
import argparse
import sys
import time

import logging
logging.basicConfig(level=logging.INFO)

sys.path.append('../')
from obswebsocket import obsws, requests  # noqa: E402

def compute_video_peak(video_file):
	"""Detect when the sync video flashes."""

	# load the video file and detect framerate
	video_stream = cv2.VideoCapture(video_file)
	fps = video_stream.get(cv2.CAP_PROP_FPS)

	# read first frame of the video
	success,image = video_stream.read()
	brightness = []

	# begin looping over each video frame
	while success:

		# split image to LAB colorspace. L captures lightness (intensity)
		L, A, B = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2LAB))

		# compute the average brightness of the L channel
		L_mean = np.mean(L)

		# store the average brightness and read the next video frame
		brightness.append(L_mean)
		success,image= video_stream.read()
	
	# find the brightest frame
	peak_video = np.argmax(brightness)

	return (fps, peak_video)

def compute_audio_peak(video_file, fps):
	"""Detect when the sync video bleeps."""

	# extract audio from video and store as temp wav file
	audio_stream = str(os.path.splitext(video_file)[0]) + ".wav"		
	ffmpeg.input(video_file).output(audio_stream).run()

	# read waveform and sampling rate
	y,sr = librosa.load(audio_stream, sr=None)

	# find the frame of the audio peak
	peak_audio = fps*np.argmax(y)/sr

	# cleanup
	os.unlink(audio_stream)
	
	return peak_audio
	
if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='hate5sync')
	parser.add_argument('--infile', help="path to file")
	parser.add_argument('--dir', help="path to directory")
	parser.add_argument('--host', default="localhost", help="OBS websocket host")
	parser.add_argument('--port', type=int, default=4444, help="OBS websocket port")
	parser.add_argument('--pw', default="secret", help="OBS websocket password")
	parser.add_argument('--src', help="OBS source name to be offset")
	args = parser.parse_args()

	# connect to OBS websocket
	ws = obsws(args.host, args.port, args.pw)
	ws.connect()

	# if recorded file is passed in, use it
	if args.infile:
		video_file = args.infile
	else:
		# if recording dir is passed in, use it
		if args.dir:
			rec_folder = args.dir

		# otherwise get the recording dir from OBS
		else:
			folder = ws.call(requests.GetRecordingFolder())
			rec_folder = folder.getRecFolder()

		# get the most recent video file from the dir
		list_of_files = glob.glob(os.path.join(rec_folder, "*")) 
		video_file = max(list_of_files, key=os.path.getctime)

	# if OBS source name is set, use it
	if args.src:
		src = args.src

	# else prompt the user to choose the source to be offset
	else:
		msg = "Choose the OBS Source to be offset"
		title = "OBS Source List"
		source_list = ws.call(requests.GetSourcesList())
		sources = [s['name'] for s in source_list.getSources()]
		src = easygui.choicebox(msg, title, sources)

	# compute the video peak
	(fps, peak_video) = compute_video_peak(video_file)

	# compute the audio peak
	peak_audio = compute_audio_peak(video_file, fps)

	# find the difference in seconds between audio/video peaks
	delay = (peak_video - peak_audio)/fps

	# automatically update the source to the computed delay (in nanoseconds)
	ws.call(requests.SetSyncOffset(src, delay*1000000000))
	easygui.msgbox("A delay of %.2f ms has been applied to %s" % (delay*1000, src))

	# disconnect from websocket
	ws.disconnect()