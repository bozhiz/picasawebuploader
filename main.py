#! /usr/bin/python
# -*- coding: UTF-8 -*-
#
# Upload directories of videos and pictures to Picasa Web Albums
#
# Requires:
#   Python 2.7
#   gdata 2.0 python library
#   sips command-line image processing tools.
#
# Copyright (C) 2011 Jack Palevich, All Rights Reserved
#
# Contains code from http://nathanvangheem.com/news/moving-to-picasa-update
#
# https://github.com/jackpal/picasawebuploader
# https://github.com/MicOestergaard/picasawebuploader

import sys
if sys.version_info < (2,7):
    sys.stderr.write("This script requires Python 2.7 or newer.\n")
    sys.stderr.write("Current version: " + sys.version + "\n")
    sys.stderr.flush()
    sys.exit(1)

import argparse
import atom
import atom.service
import filecmp
import gdata
import gdata.photos.service
import gdata.media
import gdata.geo
import gdata.gauth
import getpass
import httplib2
import os
import pyexiv2
import subprocess
import tempfile
import time
import webbrowser

from datetime import datetime, timedelta
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from gdata.photos.service import GPHOTOS_INVALID_ARGUMENT, GPHOTOS_INVALID_CONTENT_TYPE, GooglePhotosException

PICASA_MAX_FREE_IMAGE_DIMENSION = 2048
PICASA_MAX_VIDEO_SIZE_BYTES = 104857600
PICASA_MAX_PICTURES_PER_ALBUM = 2000
PICASA_MAX_RET_ENTRY = 1000

try:
    from PIL import Image
    HAS_PIL_IMAGE = True
except:
    HAS_PIL_IMAGE = False

class VideoEntry(gdata.photos.PhotoEntry):
    pass

gdata.photos.VideoEntry = VideoEntry

def InsertVideo(self, album_or_uri, video, filename_or_handle, content_type='image/jpeg'):
    """Copy of InsertPhoto which removes protections since it *should* work"""
    try:
        assert(isinstance(video, VideoEntry))
    except AssertionError:
        raise GooglePhotosException({'status':GPHOTOS_INVALID_ARGUMENT,
            'body':'`video` must be a gdata.photos.VideoEntry instance',
            'reason':'Found %s, not PhotoEntry' % type(video)
        })
    try:
        majtype, mintype = content_type.split('/')
        #assert(mintype in SUPPORTED_UPLOAD_TYPES)
    except (ValueError, AssertionError):
        raise GooglePhotosException({'status':GPHOTOS_INVALID_CONTENT_TYPE,
            'body':'This is not a valid content type: %s' % content_type,
            'reason':'Accepted content types:'
        })
    if isinstance(filename_or_handle, (str, unicode)) and \
        os.path.exists(filename_or_handle): # it's a file name
        mediasource = gdata.MediaSource()
        mediasource.setFile(filename_or_handle, content_type)
    elif hasattr(filename_or_handle, 'read'):# it's a file-like resource
        if hasattr(filename_or_handle, 'seek'):
            filename_or_handle.seek(0) # rewind pointer to the start of the file
        # gdata.MediaSource needs the content length, so read the whole image
        file_handle = StringIO.StringIO(filename_or_handle.read())
        name = 'image'
        if hasattr(filename_or_handle, 'name'):
            name = filename_or_handle.name
        mediasource = gdata.MediaSource(file_handle, content_type,
            content_length=file_handle.len, file_name=name)
    else: #filename_or_handle is not valid
        raise GooglePhotosException({'status':GPHOTOS_INVALID_ARGUMENT,
            'body':'`filename_or_handle` must be a path name or a file-like object',
            'reason':'Found %s, not path name or object with a .read() method' % \
            type(filename_or_handle)
        })

    if isinstance(album_or_uri, (str, unicode)): # it's a uri
        feed_uri = album_or_uri
    elif hasattr(album_or_uri, 'GetFeedLink'): # it's a AlbumFeed object
        feed_uri = album_or_uri.GetFeedLink().href

    try:
        return self.Post(video, uri=feed_uri, media_source=mediasource,
            converter=None)
    except gdata.service.RequestError as e:
        raise GooglePhotosException(e.args[0])

gdata.photos.service.PhotosService.InsertVideo = InsertVideo

token_expire = datetime.utcnow()

def OAuth2Login():
    configdir = os.path.expanduser(config_dir)
    client_secrets = os.path.join(configdir, secret_file)
    credential_store = os.path.join(configdir, store_file)

    storage = Storage(credential_store)
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        flow = flow_from_clientsecrets(client_secrets, scope=scope, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
        uri = flow.step1_get_authorize_url()
        print uri + "\r\n"
        print "copy the uri to web browser to get the authentication code and enter it\r\n"
        webbrowser.open(uri)
        code = raw_input('Enter the authentication code: ').strip()
        credentials = flow.step2_exchange(code)

    global token_expire
    token_expire = credentials.token_expiry
    if ( token_expire - datetime.utcnow()) < timedelta(minutes=5):
        http = httplib2.Http()
        http = credentials.authorize(http)
        credentials.refresh(http)
        token_expire = credentials.token_expiry
        print 'refresh token in login'

    print "Token will expire at ", token_expire
    storage.put(credentials)

    return gdata.photos.service.PhotosService(source=user_agent,
                                                   email=email,
                                                   additional_headers={'Authorization' : 'Bearer %s' % credentials.access_token})

def RefreshToken():
    global token_expire
    global gd_client
    
    if (token_expire - datetime.utcnow()) < timedelta(minutes=5):
        print 'Refresh token, it will expire in 5 minutes, refreshing...'
        gd_client = OAuth2Login()
        #print gd_client

def protectWebAlbums():
    albums = gd_client.GetUserFeed()
    for album in albums.entry:
        # print 'title: %s, number of photos: %s, id: %s summary: %s access: %s\n' % (album.title.text,
        #  album.numphotos.text, album.gphoto_id.text, album.summary.text, album.access.text)
        needUpdate = False
        if album.summary.text == 'test album':
            album.summary.text = ''
            needUpdate = True
        if album.access.text != 'private':
            album.access.text = 'private'
            needUpdate = True
        # print album
        if needUpdate:
            print "updating " + album.title.text
            try:
                updated_album = gd_client.Put(album, album.GetEditLink().href,
                        converter=gdata.photos.AlbumEntryFromString)
            except gdata.service.RequestError, e:
                print "Could not update album: " + str(e)

def getWebAlbums():
    albums = gd_client.GetUserFeed()
    d = {}
    for album in albums.entry:
        title = album.title.text
        if title in d:
          print "Duplicate web album:" + title
        else:
          d[title] = album
        # print 'title: %s, number of photos: %s, id: %s' % (album.title.text,
        #    album.numphotos.text, album.gphoto_id.text)
        # print vars(album)
    return d

def findAlbum(title):
    albums = gd_client.GetUserFeed()
    for album in albums.entry:
        if album.title.text == title:
            return album
    return None

def createAlbum(title):
    print "Creating album " + title
    # public, private, protected. private == "anyone with link"
    album = gd_client.InsertAlbum(title=title, summary='', access='private')
    return album

def findOrCreateAlbum(title):
    delay = 1
    while True:
        try:
            album = findAlbum(title)
            if not album:
                album = createAlbum(title)
            return album
        except gdata.photos.service.GooglePhotosException, e:
            print "caught exception " + str(e)
            print "sleeping for " + str(delay) + " seconds"
            time.sleep(delay)
            delay = delay * 2

def postPhoto(album, filename):
    album_url = '/data/feed/api/user/%s/albumid/%s' % (gd_client.email, album.gphoto_id.text)
    photo = gd_client.InsertPhotoSimple(album_url, 'New Photo',
            'Uploaded using the API', filename, content_type='image/jpeg')
    return photo

def postPhotoToAlbum(photo, album):
    album = findOrCreateAlbum(args.album)
    photo = postPhoto(album, args.source)
    return photo

def getWebPhotosForAlbum(album):
    total = int(album.numphotos.text)
    ret = 0
    start = 1
    p = []
    while start <= total:
        if total - start + 1 > PICASA_MAX_RET_ENTRY:
            ret = PICASA_MAX_RET_ENTRY
        else:
            ret = total - start + 1
            
        photos = gd_client.GetFeed(
                '/data/feed/api/user/%s/albumid/%s?kind=photo&start-index=%d&max-results=%d' % (
                gd_client.email, album.gphoto_id.text, start, ret))
        
        start += ret
        p += photos.entry

    if total != len(p):
        print ('Only %d photos retrieved from album %s, total %d' % 
            (len(p), album.title.text, total))
    # else:
    #     print ('All %d photos retrieved in album %s' % (total, album.title.text))

    return p

allExtensions = {}

# key: extension, value: type
knownExtensions = {
    '.png': 'image/png',
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.avi': 'video/avi',
    '.wmv': 'video/wmv',
    '.3gp': 'video/3gp',
    '.m4v': 'video/m4v',
    '.mp4': 'video/mp4',
    '.mov': 'video/mov'
    }

def getContentType(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in knownExtensions:
        return knownExtensions[ext]
    else:
        return None

def accumulateSeenExtensions(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in allExtensions:
        allExtensions[ext] = allExtensions[ext] + 1
    else:
        allExtensions[ext] = 1

def isMediaFilename(filename):
    accumulateSeenExtensions(filename)
    return getContentType(filename) != None

def visit(arg, dirname, names):
    basedirname = os.path.basename(dirname)
    if basedirname.startswith('.'):
        return
    mediaFiles = [name for name in names if not name.startswith('.') and isMediaFilename(name) and
        os.path.isfile(os.path.join(dirname, name))]
    count = len(mediaFiles)
    if count <= 0:
        print ('No file in directory %s' % dirname)
    elif count <= PICASA_MAX_PICTURES_PER_ALBUM:
        arg[dirname] = {'files': sorted(mediaFiles)}
    else:
        print ('The files(count %d) in directory %s is larger than %d, please split the directory' % 
            (count, dirname, PICASA_MAX_PICTURES_PER_ALBUM))
        exit()

def findMedia(source):
    hash = {}
    os.path.walk(source, visit, hash)
    return hash

def findDupDirs(photos):
    d = {}
    for i in photos:
        base = os.path.basename(i)
        if base in d:
            print "duplicate " + base + ":\n" + i + ":\n" + d[base]
            dc = filecmp.dircmp(i, d[base])
            print dc.diff_files
        d[base] = i
    # print [len(photos[i]['files']) for i in photos]

def toBaseName(photos):
    d = {}
    for i in photos:
        base = os.path.basename(i)
        if base in d:
            print "duplicate " + base + ":\n" + i + ":\n" + d[base]['path']
            raise Exception("duplicate base")
        p = photos[i]
        p['path'] = i
        d[base] = p
    return d

def compareLocalToWeb(local, web):
    localOnly = []
    both = []
    webOnly = []
    for i in local:
        if i in web:
            both.append(i)
        else:
            localOnly.append(i)
    for i in web:
        if i not in local:
            webOnly.append(i)
    return {'localOnly' : localOnly, 'both' : both, 'webOnly' : webOnly}

def compareLocalToWebDir(localAlbum, webPhotoDict):
    localOnly = []
    both = []
    webOnly = []
    for i in localAlbum:
        if i in webPhotoDict:
            both.append(i)
        else:
            localOnly.append(i)
    for i in webPhotoDict:
        if i not in localAlbum:
            print ('Web Only %s' % i)
            webOnly.append(i)
    return {'localOnly' : localOnly, 'both' : both, 'webOnly' : webOnly}

def syncDirs(dirs, local, web):
    for dir in dirs:
        print ('Sync dir/album %s' % web[dir].title.text)
        syncDir(dir, local[dir], web[dir])

def syncDir(dir, localAlbum, webAlbum):
    webPhotos = getWebPhotosForAlbum(webAlbum)
    webPhotoDict = {}
    duplicated = []
    for photo in webPhotos:
        title = photo.title.text
        if title in webPhotoDict:
            print "duplicate web photo: " + webAlbum.title.text + " " + title
            duplicated.append(photo)
        else:
            webPhotoDict[title] = photo
    
    # delete duplicated photos
    for photo in duplicated:
        title = photo.title.text
        print "Delete duplicate web photo: " + webAlbum.title.text + " " + title
        gd_client.Delete(photo)
    
    # upload local only photos
    report = compareLocalToWebDir(localAlbum['files'], webPhotoDict)
    localOnly = report['localOnly']
    for f in localOnly:
        localPath = os.path.join(localAlbum['path'], f)
        upload(localPath, webAlbum, f)

def uploadDirs(dirs, local):
    for dir in dirs:
        print ('Upload dir %s' % local[dir]['path'])
        uploadDir(dir, local[dir])

def uploadDir(dir, localAlbum):
    webAlbum = findOrCreateAlbum(dir)
    for f in localAlbum['files']:
        localPath = os.path.join(localAlbum['path'], f)
        upload(localPath, webAlbum, f)

# Global used for a temp directory
gTempDir = ''

def getTempPath(localPath):
    baseName = os.path.basename(localPath)
    global gTempDir
    if gTempDir == '':
        gTempDir = tempfile.mkdtemp('imageshrinker')
    tempPath = os.path.join(gTempDir, baseName)
    return tempPath

def imageMaxDimension(path):
    if (HAS_PIL_IMAGE):
        return imageMaxDimensionByPIL(path)
    output = subprocess.check_output(['sips', '-g', 'pixelWidth', '-g',
        'pixelHeight', path])
    lines = output.split('\n')
    w = int(lines[1].split()[1])
    h = int(lines[2].split()[1])
    return max(w,h)

def imageMaxDimensionByPIL(path):
    try:
        img = Image.open(path)
    except IOError:
        print ('The file %s can\'t be identified as image' % path)
        exit()
    (w,h) = img.size
    return max(w,h)

def shrinkIfNeeded(path):
    if (HAS_PIL_IMAGE):
        return shrinkIfNeededByPIL(path)
    if imageMaxDimension(path) > PICASA_MAX_FREE_IMAGE_DIMENSION:
        print "Shrinking " + path
        imagePath = getTempPath(path)
        subprocess.check_call(['sips', '--resampleHeightWidthMax',
            str(PICASA_MAX_FREE_IMAGE_DIMENSION), path, '--out', imagePath])
        return imagePath
    return path

def shrinkIfNeededByPIL(path):
    if imageMaxDimensionByPIL(path) > PICASA_MAX_FREE_IMAGE_DIMENSION:
        print "Shrinking " + path
        imagePath = getTempPath(path)
        img = Image.open(path)
        (w,h) = img.size
        if (w>h):
            img2 = img.resize((PICASA_MAX_FREE_IMAGE_DIMENSION, (h*PICASA_MAX_FREE_IMAGE_DIMENSION)/w), Image.ANTIALIAS)
        else:
            img2 = img.resize(((w*PICASA_MAX_FREE_IMAGE_DIMENSION)/h, PICASA_MAX_FREE_IMAGE_DIMENSION), Image.ANTIALIAS)
        img2.save(imagePath, 'JPEG', quality=99)

        # now copy EXIF data from original to new
        src_image = pyexiv2.ImageMetadata(path)
        src_image.read()
        dst_image = pyexiv2.ImageMetadata(imagePath)
        dst_image.read()
        src_image.copy(dst_image, exif=True)
        # overwrite image size based on new image
        dst_image["Exif.Photo.PixelXDimension"] = img2.size[0]
        dst_image["Exif.Photo.PixelYDimension"] = img2.size[1]
        dst_image.write()

        return imagePath
    return path

def upload(localPath, album, fileName):
    global no_resize
    global upload_movie
    contentType = getContentType(fileName)

    if contentType.startswith('image/'):
        if no_resize:
            imagePath = localPath
        else:
            imagePath = shrinkIfNeeded(localPath)

        isImage = True
        picasa_photo = gdata.photos.PhotoEntry()
    else:
        if not upload_movie:
            return

        size = os.path.getsize(localPath)

        # tested by cpbotha on 2013-05-24
        # this limit still exists
        if size > PICASA_MAX_VIDEO_SIZE_BYTES:
            print "Video file too big to upload: " + str(size) + " > " + str(PICASA_MAX_VIDEO_SIZE_BYTES)
            return
        imagePath = localPath
        isImage = False
        picasa_photo = VideoEntry()
    
    
    print "Uploading " + localPath

    picasa_photo.title = atom.Title(text=fileName)
    picasa_photo.summary = atom.Summary(text='', summary_type='text')
    delay = 1

    while True:
        try:
            RefreshToken()
            
            if isImage:
                gd_client.InsertPhoto(album, picasa_photo, imagePath, content_type=contentType)
            else:
                gd_client.InsertVideo(album, picasa_photo, imagePath, content_type=contentType)
            break
        except gdata.photos.service.GooglePhotosException, e:
          print "Got exception " + str(e)
          print "retrying in " + str(delay) + " seconds"
          time.sleep(delay)
          delay = delay * 2

    # delete the temp file that was created if we shrank an image:
    if imagePath != localPath:
        os.remove(imagePath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload pictures/videos to picasa web albums / Google+.')
    parser.add_argument('--email', help='the google account email to use (example@gmail.com)', required=True)
    parser.add_argument('--source', help='the directory to upload', required=True)
    parser.add_argument('--no_resize', help="Do not resize images, i.e., upload photos with original size.", action='store_true')
    parser.add_argument('--video', help="upload videos, i.e., upload videos.", action='store_true')
    
    args = parser.parse_args()

    email = args.email
    
    source = args.source
    if not os.path.exists(source):
        print ('Source %s is not exist' % (source))
        exit()

    if args.no_resize:
        print "*** Images will be uploaded at original size."
    else:
        print "*** Images will be resized to 2048 pixels."
    no_resize = args.no_resize

    if args.video:
        print "*** upload videos. "
    upload_movie = args.video

    config_dir = '~/.config/picasawebuploader'
    secret_file = 'client_secrets.json'
    store_file = 'credentials.dat'
    scope='https://picasaweb.google.com/data/'
    user_agent='PicasaAlbumsSync'

    # options for oauth2 login
    gd_client = OAuth2Login()
    
    # protectWebAlbums()
    webAlbums = getWebAlbums()
    localAlbums = toBaseName(findMedia(source))
    albumDiff = compareLocalToWeb(localAlbums, webAlbums)
    # print ('both: %s' % albumDiff['both'])
    # print ('localOnly: %s' % albumDiff['localOnly'])
    # print ('webOnly: %s' % albumDiff['webOnly'])

    syncDirs(albumDiff['both'], localAlbums, webAlbums)
    uploadDirs(albumDiff['localOnly'], localAlbums)
