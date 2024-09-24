import sys
from urllib.parse import urlencode, parse_qsl, quote_plus
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from urllib.request import urlopen, build_opener, install_opener
import json
from functools import lru_cache
import time
import xbmcvfs

# Plugin constants
_URL = sys.argv[0]
_HANDLE = int(sys.argv[1])
_addon = xbmcaddon.Addon(id=_URL[9:-1])
_plugin = _addon.getAddonInfo("name")
_version = _addon.getAddonInfo("version")

xbmc.log(f'[PLUGIN] {_plugin}: version {_version} initialized', xbmc.LOGINFO)
xbmc.log(f'[PLUGIN] {_plugin}: addon {_addon}', xbmc.LOGINFO)

_CATEGORIES = [_addon.getLocalizedString(30001),
               _addon.getLocalizedString(30002),
               _addon.getLocalizedString(30003),
               _addon.getLocalizedString(30004)]

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36"

chapter_cache = {}

@lru_cache(maxsize=100)
def get_chapters(episode):
    xbmc.log(f"[Gronkh.tv] Fetching chapters for episode {episode}", xbmc.LOGINFO)
    if episode in chapter_cache:
        xbmc.log(f"[Gronkh.tv] Chapters found in cache for episode {episode}", xbmc.LOGINFO)
        return chapter_cache[episode]
    
    req = urlopen(f'https://api.gronkh.tv/v1/video/info?episode={episode}')
    content = req.read().decode("utf-8")
    chapters = json.loads(content)["chapters"]
    
    chapter_cache[episode] = chapters
    xbmc.log(f"[Gronkh.tv] Fetched {len(chapters)} chapters for episode {episode}", xbmc.LOGINFO)
    return chapters

def get_url(**kwargs):
    return '{}?{}'.format(_URL, urlencode(kwargs))

def get_categories():
    return _CATEGORIES

def get_playlist_url(episode):
    pl = urlopen("https://api.gronkh.tv/v1/video/playlist?episode=" + str(episode))
    playlist_url = json.loads(pl.read().decode("utf-8"))["playlist_url"]
    return playlist_url

def get_videos(category, offset=0, search_str=""):
    videos = []
    if category == _CATEGORIES[0]:
        req = urlopen("https://api.gronkh.tv/v1/video/discovery/recent")
        content = req.read().decode("utf-8")
        videos = json.loads(content)["discovery"]
    elif category == _CATEGORIES[1]:
        req = urlopen("https://api.gronkh.tv/v1/video/discovery/views")
        content = req.read().decode("utf-8")
        videos = json.loads(content)["discovery"]
    elif category == _CATEGORIES[2]:
        OFFSET = offset
        NUM = 25
        req = urlopen(f'https://api.gronkh.tv/v1/search?sort=date&offset={OFFSET}&first={NUM}')
        content = req.read().decode("utf-8")
        videos = json.loads(content)["results"]["videos"]
    elif category == _CATEGORIES[3]:
        search_query = search_str if search_str != "" else xbmcgui.Dialog().input("Suche", type=xbmcgui.INPUT_ALPHANUM)
        while len(search_query) < 3:
            if search_query == "":
                return videos, ""
            xbmcgui.Dialog().ok(_plugin, _addon.getLocalizedString(30101))
            search_query = search_str if search_str != "" else xbmcgui.Dialog().input("Suche", type=xbmcgui.INPUT_ALPHANUM)
        req = urlopen(f'https://api.gronkh.tv/v1/search?query={quote_plus(search_query)}')
        content = req.read().decode("utf-8")
        videos = json.loads(content)["results"]["videos"]
    return videos, search_query if category == _CATEGORIES[3] else ""

def list_categories():
    xbmcplugin.setPluginCategory(_HANDLE, 'Streams und Let\'s Plays (mit Herz)')
    xbmcplugin.setContent(_HANDLE, 'videos')
    categories = get_categories()
    for category in categories:
        list_item = xbmcgui.ListItem(label=category)
        list_item.setInfo('video', {'title': category,
                                    'genre': 'Streams und Let\'s Plays',
                                    'mediatype': 'video'})
        url = get_url(action='listing', category=category)
        is_folder = True
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(_HANDLE)

def list_videos(category, offset=0, search_str=""):
    xbmcplugin.setPluginCategory(_HANDLE, category)
    xbmcplugin.setContent(_HANDLE, 'videos')
    videos, query = get_videos(category, offset, search_str)

    for video in videos:
        list_item = xbmcgui.ListItem(label=video['title'])
        ep = video['episode']

        cm = []
        chapters = get_chapters(ep)
        chapters_content = []
        for c in chapters:
            title = str(c.get("title"))
            offset = int(c.get("offset"))
            percentage = float(offset) / float(video['video_length']) * 100.0
            cm.append((f'[{seconds_to_time(offset)}] | {title}', f'RunPlugin(plugin://plugin.video.gronkhtv/?action=jump_to_chapter&episode={ep}&offset={offset})'))
            chapters_content.append(f'[{seconds_to_time(offset)}] | {title}')
        list_item.addContextMenuItems(cm)
        plot = '\n'.join(chapters_content)

        tag = list_item.getVideoInfoTag()
        tag.setMediaType('video')
        tag.setTitle(video['title'])
        tag.setGenres(['Streams und Let\'s Plays'])
        tag.setDuration(video['video_length'])
        tag.setEpisode(ep)
        tag.setDateAdded(video['created_at'])
        tag.setPremiered(video['created_at'])
        tag.setFirstAired(video['created_at'])
        tag.setPlot(plot)

        list_item.setArt({'thumb': video['preview_url'], 'icon': video['preview_url'], 'fanart': video['preview_url']})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play', video=video['episode'])
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

    if category == _CATEGORIES[2] and len(videos) == 25 and videos[-1]['episode'] != 1:
        add_more_item(category, offset)
    elif category == _CATEGORIES[3]:
        handle_search_results(videos, query)

    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(_HANDLE)

def add_more_item(category, offset):
    list_item = xbmcgui.ListItem(label="... mehr")
    list_item.setInfo('video', {'title': "... mehr", 'genre': 'Streams und Let\'s Plays', 'mediatype': 'video'})
    url = get_url(action='listing', category=category, offset=int(offset)+25)
    xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, True)

def handle_search_results(videos, query):
    if not videos:
        xbmc.log(f'[gronkh.tv] Kein Titel bei der Suche nach "{query}" gefunden', xbmc.LOGINFO)
        list_item = xbmcgui.ListItem(label=f'Kein Titel unter "{query}" gefunden')
        list_item.setInfo('video', {'title': f'Kein Titel bei der Suche nach "{query}" gefunden',
                                    'genre': 'Streams und Let\'s Plays',
                                    'mediatype': 'video'})
        url = get_url(action='listing', category=_CATEGORIES[3])
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, True)
    else:
        xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_DATEADDED)

def play_video(path, episode):
    xbmc.log(f"[Gronkh.tv] Playing video: {path}, episode: {episode}", xbmc.LOGINFO)
    play_item = xbmcgui.ListItem(path=path)
    play_item.setProperty('IsPlayable', 'true')

    resume_point = get_resume_point(episode)
    xbmc.log(f"[Gronkh.tv] Resume point: {resume_point}", xbmc.LOGINFO)
    
    if resume_point > 0:
        resume_time = int(resume_point)
        play_item.setInfo('video', {'resumetime': resume_time})
        play_item.setInfo('video', {'totaltime': int(get_total_time(episode))})
    
    xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)
    
    monitor_playback(episode)       

def monitor_playback(episode):
    player = xbmc.Player()
    while not player.isPlayingVideo():
        xbmc.sleep(100)
    
    while player.isPlayingVideo():
        try:
            current_time = player.getTime()
            total_time = player.getTotalTime()
            save_resume_point(episode, current_time, total_time)
            xbmc.log(f"[Gronkh.tv] Saved resume point: {current_time}/{total_time}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"[Gronkh.tv] Error saving resume point: {str(e)}", xbmc.LOGERROR)
        xbmc.sleep(1000)

def get_resume_point(episode):
    try:
        with xbmcvfs.File(f'special://profile/addon_data/plugin.video.gronkhtv/resume_points/{episode}.txt') as f:
            return float(f.read() or '0')
    except Exception as e:
        xbmc.log(f"[Gronkh.tv] Error getting resume point for episode {episode}: {str(e)}", xbmc.LOGERROR)
        return 0

def save_resume_point(episode, current_time, total_time):
    try:
        resume_point_dir = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.gronkhtv/resume_points/')
        if not xbmcvfs.exists(resume_point_dir):
            xbmcvfs.mkdirs(resume_point_dir)
        
        with xbmcvfs.File(f'{resume_point_dir}/{episode}.txt', 'w') as f:
            f.write(str(current_time))
    except Exception as e:
        xbmc.log(f"[Gronkh.tv] Error saving resume point for episode {episode}: {str(e)}", xbmc.LOGERROR)

def get_total_time(episode):
    try:
        with xbmcvfs.File(f'special://profile/addon_data/plugin.video.gronkhtv/total_times/{episode}.txt') as f:
            return float(f.read() or '0') 
    except Exception as e:
        xbmc.log(f"[Gronkh.tv] Error getting total time for episode {episode}: {str(e)}", xbmc.LOGERROR)
        return 0

def jump_to_chapter(params):
    episode = params['episode']
    offset = params['offset']
    xbmc.log(f"[Gronkh.tv] Jumping to chapter in episode {episode} at offset {offset}", xbmc.LOGINFO)
    player = xbmc.Player()
    
    if not player.isPlayingVideo():
        url = get_playlist_url(episode)
        xbmc.log(f"[Gronkh.tv] Starting playback of {url}", xbmc.LOGINFO)
        player.play(url)
        
        # Wait for playback to start
        start_time = time.time()
        while not player.isPlayingVideo() and time.time() - start_time < 10:
            xbmc.sleep(100)
    
    if player.isPlayingVideo():
        xbmc.log(f"[Gronkh.tv] Seeking to offset {offset}", xbmc.LOGINFO)
        player.seekTime(float(offset))
    else:
        xbmc.log("[Gronkh.tv] Failed to start playback", xbmc.LOGERROR)

def router(paramstring):
    xbmc.log(f"[Gronkh.tv] Router called with params: {paramstring}", xbmc.LOGINFO)
    params = dict(parse_qsl(paramstring))

    action_handlers = {
        'listing': handle_listing,
        'play': handle_play,
        'jump_to_chapter': jump_to_chapter
    }

    try:
        if params:
            action = params.get('action')
            if action in action_handlers:
                action_handlers[action](params)
            else:
                raise ValueError(f'Invalid action: {action}')
        else:
            list_categories()
    except Exception as e:
        xbmc.log(f"[Gronkh.tv] Error in router: {str(e)}", xbmc.LOGERROR)

    xbmc.log("[Gronkh.tv] Router finished", xbmc.LOGINFO)

def handle_listing(params):
    list_videos(params['category'], params.get('offset', '0'), params.get('search_str', ''))

def handle_play(params):
    play_video(get_playlist_url(params['video']), params['video'])

def seconds_to_time(s):
    h = int(s / 60 / 60)
    m = int((s / 60) % 60)
    s = int(s % 60)
    return f'{h}:{m:02d}:{s:02d}'

if __name__ == "__main__":
    opener = build_opener()
    opener.addheaders = [("User-Agent", _UA),
                         ("Accept-Encoding", "identity"),
                         ("Accept-Charset", "utf-8")]
    install_opener(opener)

    router(sys.argv[2][1:])
