# -*- coding: utf-8 -*-
# Module: main
# Author: Schattenechse
# Based on example by: Roman V. M.
# Created on: 20.02.2022
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
from urllib.parse import urlencode, parse_qsl, quote_plus
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from urllib.request import urlopen, build_opener, install_opener
import json

# Get the plugin url in plugin:// notation.
_URL = sys.argv[0]
# Get the plugin handle as an integer number.
_HANDLE = int(sys.argv[1])

# plugin constants
_addon   = xbmcaddon.Addon(id=_URL[9:-1])
_plugin  = _addon.getAddonInfo("name")
_version = _addon.getAddonInfo("version")

xbmc.log(f'[PLUGIN] {_plugin}: version {_version} initialized', xbmc.LOGINFO)
xbmc.log(f'[PLUGIN] {_plugin}: addon {_addon}', xbmc.LOGINFO)

# menu categories
_CATEGORIES = [_addon.getLocalizedString(30001),
                _addon.getLocalizedString(30002),
                _addon.getLocalizedString(30003),
                _addon.getLocalizedString(30004)]

# user agent for requests
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36"

def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{}?{}'.format(_URL, urlencode(kwargs))


def get_categories():
    """
    Get the list of video categories.

    Here you can insert some parsing code that retrieves
    the list of video categories (e.g. 'Movies', 'TV-shows', 'Documentaries' etc.)
    from some site or API.

    .. note:: Consider using `generator functions <https://wiki.python.org/moin/Generators>`_
        instead of returning lists.

    :return: The list of video categories
    :rtype: types.GeneratorType
    """

    return _CATEGORIES


def get_playlist_url(episode):
    """
    Get Playlist-URL from episode number
    Playlist-URL is in .m3u8 format (can be played by Kodi directly)
    """
    pl = urlopen("https://api.gronkh.tv/v1/video/playlist?episode=" + str(episode))
    playlist_url = json.loads(pl.read().decode("utf-8"))["playlist_url"]

    return playlist_url


def get_videos(category, offset=0, search_str=""):
    """
    Get the list of videofiles/streams.

    Here you can insert some parsing code that retrieves
    the list of video streams in the given category from some site or API.

    .. note:: Consider using `generators functions <https://wiki.python.org/moin/Generators>`_
        instead of returning lists.

    :param category: Category name
    :type category: str
    :param offset: offset for browsing/searching
    :type offset: int
    :param search_str: Search string
    :type search_str: str
    :return: the list of videos in the category
    :rtype: list

    structure of entries:
        id: int
        title: str
        created_at: str (YYYY-MM-DD HH:mm:ss)
        epsiode: int
        preview_url: str
        video_length: int
        views: int
        tags: [{id: int, title: str}]
    """
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
        while len(QUERY) < 3: # Suchbegriff muss mind. 3 Zeichen lang sein.
            if QUERY == "": # Wenn nichts gesucht wird, wird auch nichts gefunden.
                return videos, ""
            # Frage erneut nach Suchbegriff, bis mind. 3 Zeichen eingegeben wurden oder abgebrochen wurde (leerer String)
            xbmcgui.Dialog().ok(_plugin, _addon.getLocalizedString(30101))
            QUERY = search_str if search_str != "" else xbmcgui.Dialog().input("Suche", type=xbmcgui.INPUT_ALPHANUM)
        req = urlopen(f'https://api.gronkh.tv/v1/search?query={quote_plus(QUERY)}')
        content = req.read().decode("utf-8")
        entries = json.loads(content)["results"]["videos"]
        videos = entries
    return videos, QUERY


def list_categories():
    """
    Create the list of video categories in the Kodi interface.
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_HANDLE, 'Streams und Let\'s Plays (mit Herz)')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, 'videos')
    # Get video categories
    categories = get_categories()
    # Iterate through categories
    for category in categories:
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=category)
        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
##        list_item.setArt({'thumb': VIDEOS[category][0]['thumb'],
##                          'icon': VIDEOS[category][0]['thumb'],
##                          'fanart': VIDEOS[category][0]['thumb']})
        # Set additional info for the list item.
        # Here we use a category name for both properties for for simplicity's sake.
        # setInfo allows to set various information for an item.
        # For available properties see the following link:
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
        # 'mediatype' is needed for a skin to display info for this ListItem correctly.
        list_item.setInfo('video', {'title': category,
                                    'genre': 'Streams und Let\'s Plays',
                                    'mediatype': 'video'})
        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = get_url(action='listing', category=category)
        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)


def list_videos(category, offset=0, search_str=""):
    """
    Create the list of playable videos in the Kodi interface.

    :param category: Category name
    :type category: str
    :param offset: offset for browsing/searching
    :type offset: int
    :param search_str: Search string
    :type search_str: str

    structure of entries:
        id: int
        title: str
        created_at: str (YYYY-MM-DD HH:mm:ss)
        epsiode: int
        preview_url: str
        video_length: int
        views: int
        tags: [{id: int, title: str}]
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_HANDLE, category)
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, 'videos')
    # Get the list of videos in the category.
    videos, query = get_videos(category, offset, search_str)
    # Iterate through videos.
    for video in videos:
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=video['title'])
        ep = video['episode']

        # Add context menu items for chapters
        # https://alwinesch.github.io/group__python__xbmcgui__listitem.html#ga14712acc2994196012036f43eb2135c4
        # PlayMedia(media[,isdir][,1],[playoffset=xx]) -> see https://alwinesch.github.io/page__list_of_built_in_functions.html
        cm = []
        # get chapters
        req = urlopen(f'https://api.gronkh.tv/v1/video/info?episode={ep}')
        content = req.read().decode("utf-8")
        chapters = json.loads(content)["chapters"]
        chapters_content = []
        for c in chapters:
            title = str(c.get("title"))
            offset = int(c.get("offset"))
            percentage = float(offset) / float(video['video_length']) * 100.0
##            cm.append((f'jump to [{seconds_to_time(offset)}]: {title}', f'PlayMedia(media={url}, playoffset={offset})'))
            cm.append((f'jump to [{seconds_to_time(offset)}]: {title}', f'PlayerControl(SeekPercentage({percentage}))'))
            chapters_content.append(f'[{seconds_to_time(offset)}]: {title}')
        list_item.addContextMenuItems(cm)
        plot = '\n'.join(chapters_content)

        # Set additional info for the list item.
        # 'mediatype' is needed for skin to display info for this ListItem correctly.
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

##        list_item.setInfo('video', {'title': video['title'],
##                                    'genre': 'Streams und Let\'s Plays',
##                                    'mediatype': 'video',
##                                    'duration': video['video_length'],
##                                    'episode': ep,
##                                    'date': video['created_at'][:10],
##                                    'dateadded': video['created_at'],
##                                    'aired': video['created_at'],
##                                    'premiered': video['created_at'],
##                                    'plot': plot
##                                    })
        xbmc.log(video['created_at'], xbmc.LOGINFO)
        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
        list_item.setArt({'thumb': video['preview_url'], 'icon': video['preview_url'], 'fanart': video['preview_url']})
        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')
        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=play&video=http://www.vidsplay.com/wp-content/uploads/2017/04/crab.mp4
        url = get_url(action='play', video=video['episode'])
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    if category == _CATEGORIES[2] and len(videos) == 25 and videos[24]['episode'] != 1:
        list_item = xbmcgui.ListItem(label=category)
        list_item.setInfo('video', {'title': "... mehr",
                                    'genre': 'Streams und Let\'s Plays',
                                    'mediatype': 'video'})
        url = get_url(action='listing', category=category, offset=int(offset)+25)
        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    if category == _CATEGORIES[3]:
        if len(videos) == 0:
            xbmc.log(f'[gronkh.tv] Kein Titel bei der Suche nach "{query}" gefunden', xbmc.LOGINFO)
            list_item = xbmcgui.ListItem(label=f'Kein Titel unter "{query}" gefunden')
            list_item.setInfo('video', {'title': f'Kein Titel bei der Suche nach "{query}" gefunden',
                                        'genre': 'Streams und Let\'s Plays',
                                        'mediatype': 'video'})
            url = get_url(action='listing', category=category)
            # is_folder = True means that this item opens a sub-list of lower level items.
            is_folder = True
            # Add our item to the Kodi virtual folder listing.
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
        else:
            if len(videos) == 25 and False: # aktuell ist nicht mit einem Limit zu rechnen
                list_item = xbmcgui.ListItem(label=category)
                list_item.setInfo('video', {'title': '... mehr',
                                            'genre': 'Streams und Let\'s Plays',
                                            'mediatype': 'video'})
                url = get_url(action='listing', category=category, offset=int(offset)+25, search_str=query)
                # is_folder = True means that this item opens a sub-list of lower level items.
                is_folder = True
                # Add our item to the Kodi virtual folder listing.
                xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
            xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_DATEADDED)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)


def play_video(path):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            if params.get('offset'):
                if params.get('search_str'):
                    list_videos(params['category'], params['offset'], params['search_str'])
                else:
                    list_videos(params['category'], params['offset'])
            else:
                list_videos(params['category'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(get_playlist_url(params['video']))
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_categories()

def seconds_to_time(s):
    h = int(s / 60 / 60)
    m = int((s / 60) % 60)
    s = int(s % 60)
    return f'{h}:{m:02d}:{s:02d}'

if __name__ == "__main__":
    #set up headers for https requests
    opener = build_opener()
    opener.addheaders = [("User-Agent",      _UA),
                         ("Accept-Encoding", "identity"),
                         ("Accept-Charset",  "utf-8")]
    install_opener(opener)

    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
