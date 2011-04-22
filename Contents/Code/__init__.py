# EyeTV plugin for Plex for iOS, by sander1

import re, time

TITLE          = 'EyeTV'
ICON_DEFAULT   = 'icon-default.png'
ICON_PREFS     = 'icon-prefs.png'

STATUS_URL     = 'http://%s/live/status'
CHANNELS_URL   = 'http://%s/live/channels'
TUNETO_URL     = 'http://%s/live/tuneto/1/%%s/%%s/_SAFARI_PLAYER'
STREAM_URL     = 'http://%s/live/stream/%%s'
READY_URL      = 'http://%s/live/ready'

RECORDINGS_URL = 'http://%s/live/recordings/0/0/-1/-1/-date/_REC_WIFIACCESS'
VIDEO_URL      = 'http://%s/live/recordingFile/%%d/refmovie.mov'
VIDEO_THUMB    = 'http://%s/live/thumbnail/0/%%d'

####################################################################################################
def Start():
  Plugin.AddPrefixHandler('/video/eyetv', MainMenu, TITLE, ICON_DEFAULT)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='videos')

  ObjectContainer.title1 = TITLE
  ObjectContainer.content = ContainerContent.GenericVideos

  DirectoryObject.thumb = R(ICON_DEFAULT)
  VideoClipObject.thumb  = R(ICON_DEFAULT)

  # Low cachetime because of changing m3u8 urls
  HTTP.CacheTime = 0
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_6; en-us) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27'

####################################################################################################
def MainMenu():
  oc = ObjectContainer(no_cache=True)

  try:
    url = BuildUrl(STATUS_URL)
    status = JSON.ObjectFromURL(url, headers=DaaHeader(url))
    if status['isUp']:
      oc.add(DirectoryObject(key=Callback(Live), title='Live TV'))
      oc.add(DirectoryObject(key=Callback(Recordings), title='Recordings'))
    else:
      oc.header = TITLE
      oc.message = 'EyeTV is not running'
  except:
    oc.header = 'Error'
    oc.message = 'Can\'t connect to EyeTV'
    pass

  oc.add(PrefsObject(title='Preferences', thumb=R(ICON_PREFS)))

  return oc

####################################################################################################
def Live():
  oc = ObjectContainer(no_cache=True, view_group='List')
  url = BuildUrl(CHANNELS_URL)

  for channel in JSON.ObjectFromURL(url, headers=DaaHeader(url))['channelList']:
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
  oc = ObjectContainer(view_group='List')
  url = BuildUrl(RECORDINGS_URL)

  for recording in JSON.ObjectFromURL(url, headers=DaaHeader(url))['recordings']:
    if 'Reencoded Variants' in recording and 'iPhone' in recording['Reencoded Variants']:
      title = recording['info']['recording title']
      tagline = recording['info']['episode title']
      duration = int( recording['actual duration']*1000 )
      id = recording['id']
      thumb_url = BuildUrl(VIDEO_THUMB, True) % id
      video_url = BuildUrl(VIDEO_URL, True) % id

      oc.add(VideoClipObject(
        title = title,
        tagline = tagline,
        thumb = Callback(GetThumb, url=thumb_url),
        duration = duration,
        items = [
          MediaObject(
            parts = [
              PartObject(key=video_url)
            ],
            protocols = [Protocol.HTTPMP4Streaming],
            platforms = [ClientPlatform.iOS, ClientPlatform.Android],
            video_codec = VideoCodec.H264,
            audio_codec = AudioCodec.AAC
          )
        ]
      ))

  return oc

####################################################################################################
def PlayLiveVideo(serviceID):
  time.sleep(3) # Don't act too fast, especially not when switching streams
  url = BuildUrl(TUNETO_URL) % (Prefs['livetv_bandwidth'], serviceID)
  tune = JSON.ObjectFromURL(url, headers=DaaHeader(url))

  if tune['success']:
    video_url = BuildUrl(STREAM_URL, True) % tune['m3u8URL']
    ready = False
    i = 0

    while not ready:
      i = i + 1
      url = BuildUrl(READY_URL)
      ready = JSON.ObjectFromURL(url, headers=DaaHeader(url))['isReadyToStream']
      if not ready:
        if i == 30:
          break
        else:
          time.sleep(1)
      else:
        return Redirect(video_url)

  return

####################################################################################################
def BuildUrl(url, seen_from_ios=False):
  if seen_from_ios:
    url = url % ':'.join([ Prefs['eyetv_host_ios'], Prefs['eyetv_port_ios'] ])
  else:
    url = url % ':'.join([ Prefs['eyetv_host_pms'], Prefs['eyetv_port_pms'] ])

  Log(' --> BuildUrl return value: ' + url + ' (seen from iOS: ' + str(seen_from_ios) + ')')
  return url

####################################################################################################
def GetThumb(url):
  try:
    data = HTTP.Request(url, cacheTime=CACHE_1DAY).content
    return DataObject(data, 'image/jpeg')
  except:
    return Redirect(R(ICON_DEFAULT))

####################################################################################################
# Digest Access Authentication
def DaaHeader(url):
  daa_header = {}

  if Prefs['passcode']:
    try:
      headers = HTTP.Request(url).headers
    except Ex.HTTPError, error:
      header = error.headers.getheader('WWW-Authenticate')
      realm = re.search('digest realm="([^"]+)', header).group(1)
      nonce = re.search('nonce="([^"]+)', header).group(1)
      uri = re.sub('http://[^/]+', '', url)
      ha1 = Hash.MD5('eyetv:' + realm + ':' + Prefs['passcode'])
      ha2 = Hash.MD5('GET:' + uri)
      response = Hash.MD5(ha1 + ':' + nonce + ':' + ha2)
      auth = 'Digest username="eyetv", realm="%s", nonce="%s", uri="%s", response="%s"' % (realm, nonce, uri, response)
      daa_header = {'Authorization':auth}

  return daa_header
