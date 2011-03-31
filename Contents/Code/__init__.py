####################################################################################################
#
# EyeTV plugin for Plex for iOS, by sander1
# v1: 17 Mar 2011
#
# TODO:
# - Think if we need to be able to set the location of EyeTV twice: once for accessing it from
#   PMS (which can be "localhost") and once for accessing it from the iOS device (in case we
#   want to set a dynamic hostname to connect to home, this can never be "localhost" (except when
#   tunneling over SSH) -- my brain hurts)
# - Pick some logical default bandwidth values
# - Make a fresh pot of coffee
#
####################################################################################################

import time

TITLE          = 'EyeTV'
PREFIX         = '/video/eyetv'
ICON_DEFAULT   = 'icon-default.png'
ICON_PREFS     = 'icon-prefs.png'

STATUS_URL     = 'http://%s/live/status'
CHANNELS_URL   = 'http://%s/live/channels'
TUNETO_URL     = 'http://%s/live/tuneto/1/%s/%s/_SAFARI_PLAYER'
STREAM_URL     = 'http://%s/live/stream/%s'
READY_URL      = 'http://%s/live/ready'

RECORDINGS_URL = 'http://%s/live/recordings/0/0/-1/-1/-date/_REC_WIFIACCESS'
VIDEO_URL      = 'http://%s/live/recordingFile/%d/refmovie.mov'
VIDEO_THUMB    = 'http://%s/live/thumbnail/0/%d'

####################################################################################################

def Start():
  Plugin.AddPrefixHandler(PREFIX, MainMenu, TITLE, ICON_DEFAULT)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')

  ObjectContainer.title1 = TITLE
  ObjectContainer.content = ContainerContent.GenericVideos
  ObjectContainer.view_group = 'List'

  DirectoryObject.thumb = R(ICON_DEFAULT)
  VideoClipObject.thumb  = R(ICON_DEFAULT)

  # Low cachetime because of changing m3u8 urls
  HTTP.CacheTime = 1
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_6; en-us) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27'

####################################################################################################

def MainMenu():
  oc = ObjectContainer(noCache=True)

  try:
    status = JSON.ObjectFromURL(STATUS_URL % Prefs['eyetv_host'])
    if status['isUp']:
      oc.add(DirectoryObject(key=Callback(Live), title='Live TV'))
      oc.add(DirectoryObject(key=Callback(Recordings), title='Recordings'))
    else:
      oc.header = TITLE
      oc.message = 'EyeTV is not running'
  except:
    oc.header = 'Error'
    oc.message = 'Can\'t connect to EyeTV'

  oc.add(PrefsObject(title='Preferences', thumb=R(ICON_PREFS)))

  return oc

####################################################################################################

def Live():
  oc = ObjectContainer(noCache=True)
  for channel in JSON.ObjectFromURL(CHANNELS_URL % Prefs['eyetv_host'])['channelList']:
    oc.add(VideoClipObject(
      title = channel['name'],
      items = [
        MediaObject(
          parts = [
            PartObject(key=Callback(PlayLiveVideo, serviceID=channel['serviceID']))
          ],
          protocols = [Protocol.HTTPLiveStreaming],
          platforms = [ClientPlatform.iOS, ClientPlatform.Android],
          video_codec = VideoCodec.H264,
          audio_codec = AudioCodec.AAC
        )
      ]
    ))

  return oc

####################################################################################################

def Recordings():
  oc = ObjectContainer()
  for recording in JSON.ObjectFromURL(RECORDINGS_URL % Prefs['eyetv_host'])['recordings']:
    if 'Reencoded Variants' in recording and 'iPhone' in recording['Reencoded Variants']:
      title = recording['info']['recording title']
      subtitle = recording['info']['episode title']
      duration = int( recording['actual duration']*1000 )
      id = recording['id']
      thumb = VIDEO_THUMB % (Prefs['eyetv_host'], id)
      url = VIDEO_URL % (Prefs['eyetv_host'], id)

      oc.add(VideoClipObject(
        title = title,
        subtitle = subtitle,
        thumb = thumb,
        items = [
          MediaObject(
            parts = [
              PartObject(key=url)
            ],
            protocols = [Protocol.HTTPMP4Streaming],
            platforms = [ClientPlatform.iOS, ClientPlatform.Android],
            video_codec = VideoCodec.H264,
            audio_codec = AudioCodec.AAC,
            duration = duration
          )
        ]
      ))

  return oc

####################################################################################################

def PlayLiveVideo(serviceID):
  time.sleep(3) # Don't act too fast, especially not when switching streams
  tune = JSON.ObjectFromURL(TUNETO_URL % (Prefs['eyetv_host'], Prefs['livetv_bandwidth'], serviceID))

  if tune['success']:
    url = STREAM_URL % (Prefs['eyetv_host'], tune['m3u8URL'])
    ready = False
    i = 0

    while not ready:
      i = i + 1
      ready = JSON.ObjectFromURL(READY_URL % Prefs['eyetv_host'])['isReadyToStream']
      if not ready:
        if i == 30:
          break
        else:
          time.sleep(1)
      else:
        return Redirect(url)

  return
