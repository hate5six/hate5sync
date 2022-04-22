import glob
import os
import cv2
import librosa
import ffmpeg
import numpy as np
import easygui
import argparse

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

		# normalize L channel to be between 0-1
		L_norm = L/np.max(L)

		# compute the average brightness of the normalized L channel
		L_mean = np.mean(L_norm)

		# store the average brightness and read the next video frame
		brightness.append(L_mean)
		success,image= video_stream.read()
	
	# compute successive brightness difference between consecutive frames
	pairs_bright = list(((b-a) for a,b in zip(brightness, brightness[1:])))

	# find the frame consisting the biggest change in brightness
	peak_video = np.argmin(pairs_bright)

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
	args = parser.parse_args()

	if args.infile:
		video_file = args.infile
	elif args.dir:
		list_of_files = glob.glob(os.path.join(args.dir, "*")) 
		video_file = max(list_of_files, key=os.path.getctime)
	
	(fps, peak_video) = compute_video_peak(video_file)
	peak_audio = compute_audio_peak(video_file, fps)

	# find the difference in audio/video peaks and convert to milliseconds
	delay = 1000*(peak_video - peak_audio)/fps
	if delay > 0:
		easygui.msgbox("Audio is ahead. Delay it by %.2f milliseconds" % delay)
	elif delay < 0:
		easygui.msgbox("Video is ahead. Delay it by %.2f milliseconds" % abs(delay))
	else:
		easygui.msgbox("No sync offset needed.")