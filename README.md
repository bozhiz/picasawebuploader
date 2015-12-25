picasawebuploader
=================

A script that uploads photos to Google+ / Picasa Web Albums

+ Resizes large images to be less than the free limit (2048 x 2048)
+ Uploads all directories under a given directory
+ Restartable
+ Creates the albums as "private" aka "limited"
+ Automatically retries when Google data service errors out


Attention: This script is obsolete for Windows and Mac
------------------------------------------------------
It looks like Google Picasa for Windows and Mac now comes with a back up tool
that performs the same functionality as this script. If you are using a Windows
or Macintosh system, you probably should look into using the official Google
tool instead. See [Picasa](http://picasa.google.com/).

For more details, read this unofficial blog post describing the
[Google+ Auto Backup for Desktop](http://googlesystem.blogspot.com/2013/12/google-auto-backup-for-desktop.html) tool.


Installation
------------
+ Prerequisites:
  + Python 2.7
  + Google Data APIs http://code.google.com/apis/gdata/
    + gdata-2.0.16 for Python
  + Google OAuth2 APIs https://github.com/google/oauth2client.git
  + The Pillow library for Python or BSD "sips" image processing program.
	+ Pillow is available on most UNIX like systems.
    + "sips" comes pre-installed on OSX.
  + pyexiv2 module for writing correct EXIF data


Local Directory
--------------
+ Each lowest-level directory will be created as album, the album name is the folder name, don't include path
+ It will recursively lookup all directories under the "source"
+ Quota per albums, only 2000 pictures per albums could be upload.
  + When the to be uploaded directory contain more than 2000 pictures, will warning and exit
  + You should split the big directory to more small directories. 


Authentication
--------------
You need to use OAuth2 for authentication. Here is how to set it up ahead.

+ Create a project through the Google Developer Console: at https://console.developers.google.com/
  + Replace user_agent='PicasaAlbumsSync' with your registed project name in main.py
+ Under that project, create a new Client ID of type "Installed Application" under APIs & auth -> Credentials
+ Once the Client ID has been created you should click "Download JSON" and save the file as $HOME/.config/picasawebuploader/client_secrets.json 
  + You can change the location and name in main.py
+ Create empty $HOME/.config/picasawebuploader/credentials.dat 
  + You can change the location and name in main.py
  + It will be filled by next step in first time
  + It will be updated automatically if it expired or will expire in 5 minutes
+ The first time you run the application you will be asked to authorize your application through your web browser. 
  + If your web brower can't open correctly, like respbian on raspberry pi, you could copy the printed url to Windows PC web browser to open it.
  + Once you do this you will get a code which you have to copy and paste into the application.


To Do
-----
+ Unicode
+ Use multiple threads for uploading.
+ Deal with duplicate picture and folder names, both on local and web collections.
  + Currently we just throw an exception when we detect duplicate names.
# Sync the photo data time
  + Un-resize photo will changed to the time which created on cloud, not the one in local


Known Problems
--------------
+ Quota limitation on per album
  + Got exception (403, 'Forbidden', 'Photo limit reached.')
  + Only 2000 photos could be added per album
  + Split big directory to more small directories
