picasawebuploader
=================

A script that uploads photos to Google+ / Picasa Web Albums

+ Resizes large images to be less than the free limit (2048 x 2048)
+ Uploads all directories under a given directory
+ restartable
+ Creates the albums as "private" aka "limited"
+ Automatically retries when Google data service errors out
+ Google OAuth 2.0 login
+ Automatically update the secret data of Google OAuth 2.0


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
  + The PIL library for Python or BSD "sips" image processing program.
	+ PIL is available on most UNIX like systems.
    + "sips" comes pre-installed on OSX.
  + pyexiv2 module for writing correct EXIF data


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
  + It will be updated when it is expired or will be expired
+ The first time you run the application you will be asked to authorize your application through your web browser. 
  + If your web brower can't open correctly, like respbian on raspberry pi, you could copy the printed url to Windows PC web browser to open it.
  + Once you do this you will get a code which you have to copy and paste into the application.


To Do
-----
+ Unicode
+ Use multiple threads for uploading.
+ Deal with duplicate picture and folder names, both on local and web collections.
  + Currently we just throw an exception when we detect duplicate names.
+ Deal with 'Error: 17 REJECTED_USER_LIMIT' errors.
+ Quota per albums, only 2000 pictures per albums could be upload.
  + When the to be uploaded directory contain more than 2000 pictures, will warning and skip.
  + You should split the directory to small.


Known Problems
--------------
Picasa Web Albums appears to have an undocumented upload quota system that
limits uploads to a certain number of bytes per month.

Do a web search for REJECTED_USER_LIMIT to see the various discussions about
this. From reading the web forums it appears that the upload quota is reset
occasionally (possibly monthly). If you start getting REJECTED_USER_LIMIT
errors when you run this script you may have to wait a month to upload new
pictures.

Some people have reported that paying for yearly web storage will remove the
upload quota.
