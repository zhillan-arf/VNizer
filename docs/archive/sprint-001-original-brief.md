# VNizer

VNizer shall be a web app that converts uploaded PDF documents into MP4 videos of visual novel-like recordings. I will use it in two ways: (a) uploading it to my YouTube channel, (b) listening to the uploaded videos on my daily commutes, like an audiobook. The upload will be done manually and is outside of this project's scope. The uploaded documents are mostly gonna be an assortment of research papers from my university, in particular: social science, history, math, AI, robotics, and biology.

There's three projects that inspired this new project:

1. The /home/zhillan/misc/pacu project, which, among others, is a program that uses a VLM service to convert very huge PDF files into texts. That said the big PDF files and its conversion results was recently moved to /data-model/zhillan/pacu .
2. The /home/zhillan/misc/vmodel project, which, among others, is a vtubing platform based on MMD models, we'll use the model as the character that "speaks" in the video
3. The /home/zhillan/active-vision project, which, while completely unrelated, has a mature development ops environment and project directory setup framework that we'll reuse, including the part about the Standard Technical English.

Here we will develop a web app that is like this:

1. The app has three kinds of pages. 

- First, an auth page, which for now shall simply read from an .env and if the values are not configured, can simply be bypassed by clicking enter.

- Second, an upload page, in which the user can either drag and drop or browse from computer the PDF files they want to upload (can be multiple files). One file -> One long transcript text, divided into reasonable chunks -> One MP4 video. If either the PDF to text or the text to speech service is unavailable, clicking "Convert" (which triggers a health check request to those services) will fail and the user is told to come again later. The auth page also have a list of recent processes that can be used to navigate to said processes.

- Third, the download page. Once the user clicks "Convert", a process id is created. The user is then redirected to /[process id] which shows the current conversion progress and, once completed, can click download on one or all of the files. The files that are available for download: the .txt transcript, a video-less MP4 containing only the audio, and the MP4 video that has the VN-like video. If the download is still in progress, the user can just leave, and then go back to the /[process id] directory later. If the process fails during the PDF -> text conversion or the text -> video conversion, the user can click a "Retry" button on the failed subprocess.

- Fourth, an admin page in which I can see all process and file artefacts that has been created and/or is running, and I can decide to kill running processes or delete processes / files from here. I can also configure the file to text (FTT) and text to speech (TTS) services from here. I spoke of "the user", but honestly, the only one who would be using this service in the first place is me, so it's fine to have the admin page accessible without any additional auth or something. Additionally, I can also see and configure the VN avatar artefacts from here. I plan to be able to manually upload VN artefact files (probably MP4? GIF? Idk, and the assets is probably gonna be AI-generated from a separate service) to this platform for each defined mood and to delete them.

2. The PDF to text service will probably use a Qwen/Qwen3.8-27B-FP8 VLM service that'll run on this machine. The URL to the service (currently http://10.12.1.193:1812 is available for use) shall be configurable through a POST request to an API with /api/... endpoint. That way I don't need to down and restart the service if I want to change the VLM service, I can just use the API. If I change the API, any existing parsing process should be... handled appropriately, you oughta evaluate and then decide how's best to handle it. 

Here, /home/zhillan/misc/pacu's existing design choices will be authoritative. However, the end result should be chunked into many text files ready to be converted from text to speech, and importantly, the chunking should not be mathematical, but based on full sentences,  except if the sentence is long, upon which it can be divided in the middle of the sentence (although if it is the case, and if available, it is preferable to chunk it between a comma). So each chunk doesn't necessarily need to be the same size, it just need to be capped, and I decided that the cap shall be 512 characters, i.e. around the size of a Threads post (which in fact is my mental model about this problem).

Additionally, each chunk should be labeled with an emotional mood. This will be useful for picking which VN avatar to use on the chunk, more on this on no. 6.

3. The text to audio service will probably use a Qwen3-TTS-12Hz-1.7B-CustomVoice service that'll run on this machine. Unfortunately the machine is currently occupied by other project so any testing here would need to wait. The model haven't been downloaded yet and downloading it to /data-model/zhillan/VNizer and having it be deployable as a docker service will be a part of this project.

4. I delegate the protocol of transcribing tables and image figure transcription to you. You shall evaluate and then decide on how to handle such data objects in this system, probably by researching online about how others dealt with this problem. Again, the goal is to be able to listen to documents like an audiobook. 

5. I delegate the handling of DBs to you. For now the DB should be in this disk, but I plan to purchase a cloud service later and migrate it there so that I can convert lots of documents into videos. This will probably happen once the MVP has been established.

6. I delegate the handling of VN visual design and the preparation of the first VN avatar artefacts to you. /home/zhillan/misc/vmodel already have things to say about this, you can just use them.

Your task now:

1. Setup this codebase based on the protocols already implemented in /home/zhillan/active-vision project. Everything that comes after this phase should strictly use Standard Technical English.

2. Convert this brief into a more proper sprint brief (and archive this document somewhere). Then, convert them into a defined design specifications. If there are decisions that appear, I give you the autonomy to evaluate and then decide on it, noting the goals I specified in the very beginning. The scope is items 1-6 as described, including downloading the TTS model, although I'll be the one to actually deploy any docker service. The deliverable would be the finished work ready to be deployed and tested with a few PDF files I have prepared.

3. Once the PRDs are ready, convert them into backlogs ready to be implemented, phased and controlled with P01, P02, etc controller tasks. Once a phase is completed, git commit them.

4. Once the backlog are ready, implement them. All of these work shall be a sprint 001.