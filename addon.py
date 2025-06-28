import sys, json, time
from urllib.parse import urlencode, parse_qsl, quote_plus
from urllib.request import urlopen, build_opener, install_opener
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs
from functools import lru_cache

_URL, _HANDLE = sys.argv[0], int(sys.argv[1])
_addon = xbmcaddon.Addon(id=_URL[9:-1])
_PLUGIN = _addon.getAddonInfo("name")
_CATS = [_addon.getLocalizedString(i) for i in range(30001, 30005)]
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36"

xbmc.log(f"[{_PLUGIN}] Init", xbmc.LOGINFO)

chapter_cache = {}

@lru_cache(maxsize=100)
def get_chapters(ep):
    if ep in chapter_cache:
        return chapter_cache[ep]
    res = urlopen(f'https://api.gronkh.tv/v1/video/info?episode={ep}')
    data = json.loads(res.read().decode("utf-8"))
    chapter_cache[ep] = data["chapters"]
    return data["chapters"]

def get_url(**kwargs):
    return f"{_URL}?{urlencode(kwargs)}"

def get_videos(cat, off=0, query=""):
    if cat == _CATS[0]:
        url = "video/discovery/recent"
    elif cat == _CATS[1]:
        url = "video/discovery/views"
    elif cat == _CATS[2]:
        url = f"search?sort=date&offset={off}&first=25"
    else:
        query = query or xbmcgui.Dialog().input("Suche", type=xbmcgui.INPUT_ALPHANUM)
        while len(query) < 3:
            if not query: return [], ""
            xbmcgui.Dialog().ok(_PLUGIN, _addon.getLocalizedString(30005))
            query = xbmcgui.Dialog().input("Suche", type=xbmcgui.INPUT_ALPHANUM)
        url = f"search?query={quote_plus(query)}"

    base = "https://api.gronkh.tv/v1/"
    full_url = base + ("video/" + url if url.startswith("discovery") else url)
    res = urlopen(full_url).read().decode("utf-8")
    vids = json.loads(res)
    key = "discovery" if "discovery" in url else "results"
    return (vids[key]["videos"] if "videos" in vids[key] else vids[key]), query if cat == _CATS[3] else ""

def list_categories():
    xbmcplugin.setPluginCategory(_HANDLE, 'Gronkh.tv - Streams und Let\'s Plays')
    xbmcplugin.setContent(_HANDLE, 'videos')
    for cat in _CATS:
        item = xbmcgui.ListItem(label=cat)
        item.setInfo('video', {'title': cat, 'genre': 'Let\'s Plays', 'mediatype': 'video'})
        xbmcplugin.addDirectoryItem(_HANDLE, get_url(action='listing', category=cat), item, True)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(_HANDLE)

def seconds_to_time(s):
    h, m = divmod(int(s), 3600)
    m, s = divmod(m, 60)
    return f'{h}:{m:02d}:{s:02d}'

def list_videos(cat, off=0, q=""):
    vids, q = get_videos(cat, int(off), q)
    for v in vids:
        item = xbmcgui.ListItem(label=v['title'])
        ep = v['episode']
        chapters = get_chapters(ep)
        cm = [(f"[{seconds_to_time(c['offset'])}] | {c['title']}",
              f"RunPlugin(plugin://plugin.video.gronkhtv/?action=jump_to_chapter&episode={ep}&offset={c['offset']})") for c in chapters]
        item.addContextMenuItems(cm)
        tag = item.getVideoInfoTag()
        tag.setMediaType('video'); tag.setTitle(v['title']); tag.setGenres(['Let\'s Plays'])
        tag.setDuration(v['video_length']); tag.setEpisode(ep)
        tag.setDateAdded(v['created_at']); tag.setPremiered(v['created_at'])
        tag.setFirstAired(v['created_at']); tag.setPlot('\n'.join([x[0] for x in cm]))
        item.setArt({'thumb': v['preview_url'], 'fanart': v['preview_url']})
        item.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(_HANDLE, get_url(action='play', video=ep), item, False)

    if cat == _CATS[2] and len(vids) == 25 and vids[-1]['episode'] != 1:
        more = xbmcgui.ListItem(label="... mehr")
        more.setInfo('video', {'title': "... mehr"})
        xbmcplugin.addDirectoryItem(_HANDLE, get_url(action='listing', category=cat, offset=int(off)+25), more, True)

    if cat == _CATS[3] and not vids:
        item = xbmcgui.ListItem(label=f'Kein Titel unter "{q}" gefunden')
        item.setInfo('video', {'title': item.getLabel(), 'genre': 'Let\'s Plays'})
        xbmcplugin.addDirectoryItem(_HANDLE, get_url(action='listing', category=cat), item, True)

    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(_HANDLE)

def get_resume(episode, folder):
    try:
        with xbmcvfs.File(f'special://profile/addon_data/plugin.video.gronkhtv/{folder}/{episode}.txt') as f:
            return float(f.read() or '0')
    except: return 0

def save_resume(episode, curr, folder):
    path = xbmcvfs.translatePath(f'special://profile/addon_data/plugin.video.gronkhtv/{folder}/')
    if not xbmcvfs.exists(path): xbmcvfs.mkdirs(path)
    with xbmcvfs.File(f'{path}/{episode}.txt', 'w') as f:
        f.write(str(curr))

def monitor_playback(ep):
    p = xbmc.Player()
    while not p.isPlayingVideo(): xbmc.sleep(100)
    while p.isPlayingVideo():
        save_resume(ep, p.getTime(), 'resume_points')
        xbmc.sleep(1000)

def get_playlist_url(ep):
    return json.loads(urlopen(f"https://api.gronkh.tv/v1/video/playlist?episode={ep}").read())["playlist_url"]

def play_video(path, ep):
    li = xbmcgui.ListItem(path=path)
    li.setProperty('IsPlayable', 'true')
    resume = get_resume(ep, 'resume_points')
    if resume:
        li.setInfo('video', {'resumetime': int(resume), 'totaltime': int(get_resume(ep, 'total_times'))})
    xbmcplugin.setResolvedUrl(_HANDLE, True, li)
    monitor_playback(ep)

def jump_to_chapter(p):
    ep, off = p['episode'], float(p['offset'])
    pl = xbmc.Player()
    if not pl.isPlayingVideo():
        pl.play(get_playlist_url(ep))
        for _ in range(100):  # 10s max wait
            if pl.isPlayingVideo(): break
            xbmc.sleep(100)
    if pl.isPlayingVideo(): pl.seekTime(off)

def router(pstr):
    p = dict(parse_qsl(pstr))
    if not p: return list_categories()
    a = p.get('action')
    if a == 'listing': list_videos(p['category'], p.get('offset', '0'), p.get('search_str', ''))
    elif a == 'play': play_video(get_playlist_url(p['video']), p['video'])
    elif a == 'jump_to_chapter': jump_to_chapter(p)

if __name__ == "__main__":
    opener = build_opener()
    opener.addheaders = [("User-Agent", _UA), ("Accept-Encoding", "identity"), ("Accept-Charset", "utf-8")]
    install_opener(opener)
    router(sys.argv[2][1:])
