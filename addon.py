# -*- coding: utf-8 -*-
"""Module: main
Author: jamal2362
Created on: 27.01.2024
License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
"""

import sys
import json
from urllib.parse import urlencode, parse_qsl, quote_plus
from urllib.request import urlopen, build_opener, install_opener
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

# Constants
_URL = sys.argv[0]
_HANDLE = int(sys.argv[1])
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36"
_CATEGORIES = [
    xbmcaddon.Addon().getLocalizedString(i) for i in range(30001, 30005)
]

# Functions


def get_url(**kwargs):
    """Create a URL for calling the plugin recursively."""
    return '{}?{}'.format(_URL, urlencode(kwargs))


def get_playlist_url(episode):
    """Get Playlist-URL from episode number."""
    pl = urlopen(f"https://api.gronkh.tv/v1/video/playlist?episode={episode}")
    playlist_url = json.loads(pl.read().decode("utf-8"))["playlist_url"]
    return playlist_url


def get_videos(category, offset=0, search_str=""):
    """Get the list of videofiles/streams."""
    videos = []
    QUERY = ""
    if category == _CATEGORIES[0]:
        req = urlopen("https://api.gronkh.tv/v1/video/discovery/recent")
        content = req.read().decode("utf-8")
        entries = json.loads(content)["discovery"]
        videos = entries
    elif category == _CATEGORIES[1]:
        req = urlopen("https://api.gronkh.tv/v1/video/discovery/views")
        content = req.read().decode("utf-8")
        entries = json.loads(content)["discovery"]
        videos = entries
    elif category == _CATEGORIES[2]:
        OFFSET = offset
        NUM = 25 #25 is max
        req = urlopen(f'https://api.gronkh.tv/v1/search?sort=date&offset={OFFSET}&first={NUM}')
        content = req.read().decode("utf-8")
        entries = json.loads(content)["results"]["videos"]
        videos = entries
    elif category == _CATEGORIES[3]:
        QUERY = search_str if search_str != "" else xbmcgui.Dialog().input("Suche", type=xbmcgui.INPUT_ALPHANUM)
        while len(QUERY) < 3:
            if QUERY == "":
                return videos, ""
            xbmcgui.Dialog().ok(_plugin, _addon.getLocalizedString(30101))
            QUERY = search_str if search_str != "" else xbmcgui.Dialog().input("Suche", type=xbmcgui.INPUT_ALPHANUM)
        req = urlopen(f'https://api.gronkh.tv/v1/search?query={quote_plus(QUERY)}')
        content = req.read().decode("utf-8")
        entries = json.loads(content)["results"]["videos"]
        videos = entries
    return videos, QUERY


def list_categories():
    """Create the list of video categories in the Kodi interface."""
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
    """Create the list of playable videos in the Kodi interface."""
    xbmcplugin.setPluginCategory(_HANDLE, category)
    xbmcplugin.setContent(_HANDLE, 'videos')
    videos, query = get_videos(category, offset, search_str)
    for video in videos:
        list_item = xbmcgui.ListItem(label=video['title'])
        ep = video['episode']
        cm = []
        req = urlopen(f'https://api.gronkh.tv/v1/video/info?episode={ep}')
        content = req.read().decode("utf-8")
        chapters = json.loads(content)["chapters"]
        chapters_content = []
        for c in chapters:
            title = str(c.get("title"))
            offset = int(c.get("offset"))
            percentage = float(offset) / float(video['video_length']) * 100.0
            cm.append((f'jump to [{seconds_to_time(offset)}]: {title}', f'PlayerControl(SeekPercentage({percentage}))'))
            chapters_content.append(f'[{seconds_to_time(offset)}]: {title}')
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
        is_folder = False
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    if category == _CATEGORIES[2] and len(videos) == 25 and videos[24]['episode'] != 1:
        list_item = xbmcgui.ListItem(label=category)
        list_item.setInfo('video', {'title': "... mehr",
                                    'genre': 'Streams und Let\'s Plays',
                                    'mediatype': 'video'})
        url = get_url(action='listing', category=category, offset=int(offset)+25)
        is_folder = True
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    if category == _CATEGORIES[3]:
        if len(videos) == 0:
            xbmc.log(f'[gronkh.tv] Kein Titel bei der Suche nach "{query}" gefunden', xbmc.LOGINFO)
            list_item = xbmcgui.ListItem(label=f'Kein Titel unter "{query}" gefunden')
            list_item.setInfo('video', {'title': f'Kein Titel bei der Suche nach "{query}" gefunden',
                                        'genre': 'Streams und Let\'s Plays',
                                        'mediatype': 'video'})
            url = get_url(action='listing', category=category)
            is_folder = True
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
        else:
            if len(videos) == 25 and False: # aktuell ist nicht mit einem Limit zu rechnen
                list_item = xbmcgui.ListItem(label=category)
                list_item.setInfo('video', {'title': '... mehr',
                                            'genre': 'Streams und Let\'s Plays',
                                            'mediatype': 'video'})
                url = get_url(action='listing', category=category, offset=int(offset)+25, search_str=query)
                is_folder = True
                xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
            xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(_HANDLE)


def play_video(path):
    """Play a video by the provided path."""
    play_item = xbmcgui.ListItem(path=path)
    xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)


def router(paramstring):
    """Router function that calls other functions depending on the provided paramstring."""
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'listing':
            if params.get('offset'):
                if params.get('search_str'):
                    list_videos(params['category'], params['offset'], params['search_str'])
                else:
                    list_videos(params['category'], params['offset'])
            else:
                list_videos(params['category'])
        elif params['action'] == 'play':
            play_video(get_playlist_url(params['video']))
        else:
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        list_categories()


def seconds_to_time(s):
    """Convert seconds to HH:MM:SS format."""
    h = int(s / 60 / 60)
    m = int((s / 60) % 60)
    s = int(s % 60)
    return f'{h}:{m:02d}:{s:02d}'


if __name__ == "__main__":
    # Set up headers for HTTPS requests
    opener = build_opener()
    opener.addheaders = [("User-Agent",      _UA),
                         ("Accept-Encoding", "identity"),
                         ("Accept-Charset",  "utf-8")]
    install_opener(opener)

    # Call the router function and pass the plugin call parameters to it.
    router(sys.argv[2][1:])
