# hate5sync

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/fbshqualaJc/0.jpg)](https://www.youtube.com/watch?v=fbshqualaJc)

hate5sync is a dumb algorithm used to calculate the necessary offset for syncing separate audio/video sources in OBS. Play slate.mp4 on a device (ie your phone) pointed at the camera and microphone and record it within OBS. Let's call that recorded file <b>claptest.mp4</b>. For best results, cover the entire camera lens with the phone and minimize background noise. <b>Any light leaks or things besides the full black screen will trip the visual peak detector.</b> Run this script on claptest.mp4 and it will calculate the offset between the visual and acoustic peaks. The app uses OBS websockets to automatically update the offset field. Click the image above to watch a demo.

<h2>Installation:</h2>

The following dependencies are required:
<ul>
  <li><a href="https://pypi.org/project/opencv-python/" target="_blank">open-cv</a> </li>
  <li><a href="https://librosa.org/" target="_blank">librosa</a> </li>
  <li><a href="https://github.com/kkroening/ffmpeg-python" target="_blank">ffmpeg</a> </li>
  <li><a href="https://numpy.org/" target="_blank">numpy</a> </li>
  <li><a href="http://easygui.sourceforge.net/" target="_blank">easygui</a> </li>
  <li><a href="https://github.com/obsproject/obs-websocket" target="_blank">obs-websocket server</a> </li>
  <li><a href="https://github.com/Elektordi/obs-websocket-py" target="_blank">obs-websocket Python library</a> </li>
  
</ul> 

Or you can just use the requirements.txt file
```
pip install -r requirements.txt
```
or
```
conda create --name <env_name> --file requirements.txt
```

The latest version of the app automatically updates the sync offset field through OBS websockets. You will need to download OBS websockets from the link above and follow the installation instructions carefully. With OBS running, you can now run hate5sync and it will communicate directly with OBS.

<h2>Running hate5sync:</h2>

You can run hate5sync with the following arguments:
```
usage: hate5sync.py [-h] [--infile INFILE] [--dir DIR] [--host HOST] [--port PORT] [--pw PW] [--src SRC]

hate5sync

options:
  -h, --help       show this help message and exit
  --infile INFILE  path to file
  --dir DIR        path to directory
  --host HOST      OBS websocket host
  --port PORT      OBS websocket port
  --pw PW          OBS websocket password
  --src SRC        OBS source name to be offset
  ```
You can use --infile to pass in the video file recorded in OBS. If a file is not passed in the app will take the most recent file specified in --dir. If --dir is not set it will retrieve the default OBS recording directory. If you are not using the default host/port/password for OBS websockets, use the corresponding options to override the defaults. --src should be the name of source in OBS that needs the offset applied. If this option is not set you will be presented with a dialog box asking you to choose.

For example, running
```
python -i hate5sync.py --pw password --src "Mic/Aux"
```

Will retrieve the latest file recorded in OBS using, compute the delay, then automatically set the offset to the Mic/Aux source.

Personally I save the latter line to a file called <b>hate5sync.bat</b> and assign to a button via StreamDeck:<br><br>
![Alt text](demo/streamdeck.png?raw=true "streamdeck")

<h2>How it works:</h2>
The algorithm is literally so stupid. <br><br>

First it loads claptest.mp4
```
video_stream = cv2.VideoCapture(video_file)
fps = video_stream.get(cv2.CAP_PROP_FPS)
```  
Then it loops over the video frame by frame. We use open-cv to convert each frame to the LAB colorspace. All we care about the L channel, which captures lightness (intensity). L ends up being a matrix the size of the video frame (1920x1080). Then we compute the average value of that normalized matrix to get the average brightness of that image. Store that in a list called <b>brightness</b> and repeat the process on the next frame.
```
success,image = video_stream.read()
brightness = []

while success:
  L, A, B = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2LAB))
  L_mean = np.mean(L)
  brightness.append(L_mean)
  success,image= video_stream.read()
```    

If we plot the values stored in <b>brightness</b> we get something that looks like<br>
![Alt text](demo/brightness.png?raw=true "Brightness vs frame")

Next, we find the frame with the maximum brightness, which should correspond to the moment the flash appears on screen:
```
peak_video = np.argmax(brightness)
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

Finally, we take the difference between the peaks (as frames), divide it by the framerate to get the difference in seconds:
```
delay = (peak_video - peak_audio)/fps
```
<br>
That delay is then automatically applied to the specified source in OBS.