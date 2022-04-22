# hate5sync

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/fbshqualaJc/0.jpg)](https://www.youtube.com/watch?v=fbshqualaJc)

hate5sync is a dumb algorithm used to calculate the necessary offset for syncing separate audio/video sources in OBS. Play slate.mp4 on a device (ie your phone) pointed at the camera and microphone and record it within OBS. Let's call that recorded file <b>claptest.mp4</b>. For best results, cover the entire camera lens with the phone and minimize background noise. <b>Any light leaks or things besides the full black screen will trip the visual peak detector.</b> Run this script on claptest.mp4 and it will calculate the offset between the visual and acoustic peaks. Enter that value into the OBS "sync offset" field and you're done.

<h2>Installation:</h2>

The following dependencies are required:
<ul>
  <li><a href="https://pypi.org/project/opencv-python/" target="_blank">open-cv</a> </li>
  <li><a href="https://librosa.org/" target="_blank">librosa</a> </li>
  <li><a href="https://github.com/kkroening/ffmpeg-python" target="_blank">ffmpeg</a> </li>
  <li><a href="https://numpy.org/" target="_blank">numpy</a> </li>
  <li><a href="http://easygui.sourceforge.net/" target="_blank">easygui</a> </li>
</ul> 

Or you can just use the requirements.txt file
```
pip install -r requirements.txt
```
or
```
conda create --name <env_name> --file requirements.txt
```
<h2>Running hate5sync:</h2>

You can run hate5sync by pointing it to the recorded video:
```
python hate5sync.py --infile path_to_recorded_video
```
Alternatively, if you are recording videos with OBS (as shown in the demo), you can just point hate5sync to the default OBS video recording directory and it will automatically read the most recent file:
```
python hate5sync.py --dir path_to_OBS_video_directory
```

Personally I save the latter line to a file called <b>hate5sync.bat</b> and assign to a button via StreamDeck:<br><br>
![Alt text](demo/streamdeck.png?raw=true "streamdeck")

<h2>How it works:</h2>
The algorithm is literally so stupid. <br><br>

First it loads claptest.mp4
```
video_stream = cv2.VideoCapture(video_file)
fps = video_stream.get(cv2.CAP_PROP_FPS)
```  
Then it loops over the video frame by frame. We use open-cv to convert each frame to the LAB colorspace. All we care about the L channel, which captures lightness (intensity). L ends up being a matrix the size of the video frame (1920x1080). We normalize it so each value in the matrix is between 0-1. Then we compute the average value of that normalized matrix to get the average brightness of that image. Store that in a list called <b>brightness</b> and repeat the process on the next frame.
```
success,image = video_stream.read()
brightness = []

while success:
  L, A, B = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2LAB))
  L_norm = L/np.max(L)
  L_mean = np.mean(L_norm)
  brightness.append(L_mean)
  success,image= video_stream.read()
```    

If we plot the values stored in <b>brightness</b> we get something that looks like<br>
![Alt text](demo/brightness.png?raw=true "Brightness vs frame")

We could look for the max brightness value, but quick tests indicate that finding the max change in brightness is more accurate. It makes sense: if you look at the above plot the peak isn't a sharp point, it spikes up then increases for a few frames before dropping down. We care about the initial jump. For each consecutive brightness values we'll compute the successive differences, then find the frame that contained the biggest jump:

```
pairs_bright = list(((b-a) for a,b in zip(brightness, brightness[1:])))
peak_video = np.argmin(pairs_bright)
```

The audio portion is even dumber. First we'll use ffmpeg to extract the audio from claptest.mp4 and store it to a temporary wav file:
```
audio_stream = str(os.path.splitext(video_file)[0]) + ".wav"		
ffmpeg.input(video_file).output(audio_stream).run()
```

Then we'll use librosa to read in that wav file along with the sampling rate, which we'll need for finding the peak audio frame
```
y,sr = librosa.load(audio_stream, sr=None)
```
Plotting the waveform will look something like this<br>
![Alt text](demo/waveform.png?raw=true "Audio amplitude vs frame")

All we care about is the frame where the audio peaks. To get that we just need the time-series sampled wav data returned by librosa (y), and find the sample (position) with the highest value, divide it by the sampling rate (sr) to get the position in seconds, then mulitply that by the framerate (frames per second fps) to get its frame position:
```
peak_audio = fps*np.argmax(y)/sr
```

Overlaying the data we get something like this<br>
![Alt text](demo/delay.png?raw=true "amplitude and brightness peaks")

Finally, we take the difference between the peaks (as frames), divide it by the framerate to get the difference in seconds, then convert to milliseconds
```
delay = 1000*(max(peak_audio, peak_video) - min(peak_video, peak_audio))/fps
```
<br>
Game over. Enter that value into OBS' "sync offset" feature and now your audio/video sources are pretty damn close lmao.
