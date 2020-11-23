import os
from flask import session, request, redirect, render_template
import spotipy
import uuid
from app import parse
from app.citrus import mei, yuzu
from app.forms import SingleInputPlaylistForm, RecommendationForm
from app import app, caches_folder
from app.client import client_id, client_secret, redirect_uri, scope
     
def session_cache_path():
    print(session.get('uuid'))
    print(caches_folder)
    return caches_folder + session.get('uuid')

@app.route('/')
def login():
    if not session.get('uuid'):
        session['uuid'] = str(uuid.uuid4())

    auth_manager = spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope,
                                                cache_path=session_cache_path(), 
                                                show_dialog=True)

    if request.args.get("code"):
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.get_cached_token():
        auth_url = auth_manager.get_authorize_url()
        return render_template('login.html', login_url = auth_url)
    else:
        return redirect('/user')


@app.route('/logout')
def logout():
    try:
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))
    return redirect('/')


@app.route('/user')
def index():
    auth_manager = spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, cache_path=session_cache_path())
    sp = spotipy.Spotify(auth_manager=auth_manager)
    if session.get('user') is None: 
        user = sp.me()   
        info = {}
        info['name'] = user['display_name']
        info['image'] = ""  
        if len(user['images']) > 0:
            info['image'] = user['images'][0]['url']
        session['user'] = info

    parses = {}
    ''' user tracks '''
    if session.get('short-top-tracks') is not None:
        parses['short-top-tracks'] = parse.getTopFive(session['short-top-tracks'])
    if session.get('medium-top-tracks') is not None:
        parses['medium-top-tracks'] = parse.getTopFive(session['medium-top-tracks'])
    if session.get('long-top-tracks') is not None:
        parses['long-top-tracks'] = parse.getTopFive(session['long-top-tracks'])
    if session.get('saved-library-tracks') is not None:
        parses['saved-library-tracks'] = len(session['saved-library-tracks'])
    if session.get('all-playlist-tracks') is not None:
        parses['all-playlist-tracks'] = len(session['all-playlist-tracks'])
    if session.get('combined-library-playlist-tracks') is not None:
        parses['combined-tracks'] = len(session['combined-library-playlist-tracks'])


    ''' user artists '''
    if session.get('top-artists-from-combined') is not None:
        parses['combined-artists'] = len(session['top-artists-from-combined'])
    if session.get('short-top-artists-name') is not None:
        parses['short-top-artists'] = ", ".join(session['short-top-artists-name'][:5])
    if session.get('medium-top-artists-name') is not None:
        parses['medium-top-artists'] = ", ".join(session['medium-top-artists-name'][:5])
    if session.get('long-top-artists-name') is not None:
        parses['long-top-artists'] = ", ".join(session['long-top-artists-name'][:5])
    
    ''' user genres '''
    if session.get('top-genres-from-long-artist') is not None:
        parses['long-genres'] = parse.getTopFiveGenres(session['top-genres-from-long-artist'])
    if session.get('top-genres-from-medium-artist') is not None:
        parses['medium-genres'] = parse.getTopFiveGenres(session['top-genres-from-medium-artist'])
    if session.get('top-genres-from-short-artist') is not None:
        parses['short-genres'] = parse.getTopFiveGenres(session['top-genres-from-short-artist'])

    if request.method == 'POST':
        pass

    return render_template('index.html', user=session['user'], parses=parses)

@app.route('/user/top-tracks',  methods=['GET', 'POST'])
def top_tracks():
    auth_manager = spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope, cache_path=session_cache_path())
    if not auth_manager.get_cached_token():
        return redirect('/user')

    sp = spotipy.Spotify(auth_manager=auth_manager)
    tracks = []            
    time_range = None
    
    if request.method == 'POST' and "short-term" in request.form:
        if session.get('short-top-tracks') is None:
            parse.parseShortTopTracks(sp)
        tracks = session['short-top-tracks']
        time_range = 'short_term'
    if request.method == 'POST' and "medium-term" in request.form:
        if session.get('medium-top-tracks') is None:
            parse.parseMediumTopTracks(sp)
        tracks =  session['medium-top-tracks']
        time_range = 'medium_term'
    if request.method == 'POST' and "long-term" in request.form:
        if session.get('long-top-tracks') is None:
           parse.parseLongTopTracks(sp)
        tracks = session['long-top-tracks']
        time_range = 'long_term'
    return render_template('tracks_list.html', tracks=tracks, time_range=time_range, user=session['user'])

@app.route('/user/top-genres', methods=['GET', 'POST'])
def top_genres():
    auth_manager = spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope, cache_path=session_cache_path())
    if not auth_manager.get_cached_token():
        return redirect('/user')

    sp = spotipy.Spotify(auth_manager=auth_manager)
    genre_count = []
    basis = None
    
    if request.method == 'POST' and "saved-library" in request.form:
        if session.get('saved-library-tracks') is None:
            parse.parseSavedLibraryTracks(sp)
        if session.get('saved-library-genres-all') is None:
            parse.parseTopGenresFromSavedLibrary(sp)
        genre_count =  session['top-genres-from-saved-library']
        basis = 'saved-library'

    if request.method == 'POST' and 'all-playlist' in request.form:
        if session.get('all-playlist-tracks') is None:
            token = auth_manager.get_access_token(as_dict=False)
            parse.parseAllPlaylistTracks(sp, token)
        if session.get('all-playlist-genres-all') is None:    
            parse.parseTopGenresFromAllPlaylists(sp)
        genre_count = session['top-genres-from-all-playlist']
        basis = 'all-playlist'

    if request.method == 'POST' and 'combined' in request.form:
        if session.get('combined-library-playlist-tracks') is None:
            token = auth_manager.get_access_token(as_dict=False)
            parse.parseCombinedTracks(sp, token)
        if session.get('combined-track-genre-dict') is None:
            parse.parseCombinedTrackGenreDict(sp)
        if session.get('top-genres-from-combined') is None:
            parse.parseTopGenresFromCombined()
        genre_count = session['top-genres-from-combined']
        basis = 'combined'

    if request.method == 'POST' and 'long-top' in request.form:
        if session.get('long-top-tracks') is None:
            parse.parseLongTopTracks(sp)
        if session.get('long-top-genres-all') is None:
            parse.parseTopGenresFromLongTop(sp)
        genre_count = session['top-genres-from-long-top']
        basis = 'long-top'

    if request.method == 'POST' and 'medium-top' in request.form:
        if session.get('medium-top-tracks') is None:
            parse.parseMediumTopTracks(sp)
        if session.get('medium-top-genres-all') is None:
            parse.parseTopGenresFromMediumTop(sp)
        genre_count = session['top-genres-from-medium-top']
        basis = 'medium-top'

    if request.method == 'POST' and 'short-top' in request.form:
        if session.get('short-top-tracks') is None:
            parse.parseShortTopTracks(sp)
        if session.get('short-top-genres-all') is None:
            parse.parseTopGenresFromShortTop(sp)
        genre_count = session['top-genres-from-short-top']
        basis = 'short-top'

    if request.method == 'POST' and 'long-artist' in request.form:
        if session.get('long-top-artists') is None:
            parse.parseLongTopArtists(sp)
        if session.get('long-artist-genres-all') is None:
            parse.parseTopGenresFromLongArtist(sp)
        genre_count = session['top-genres-from-long-artist']
        basis = 'long-artist'

    if request.method == 'POST' and 'medium-artist' in request.form:
        if session.get('medium-top-artists') is None:
            parse.parseMediumTopArtists(sp)
        if session.get('medium-artist-genres-all') is None:
            parse.parseTopGenresFromMediumArtist(sp)
        genre_count = session['top-genres-from-medium-artist']
        basis = 'medium-artist'

    if request.method == 'POST' and 'short-artist' in request.form:
        if session.get('short-top-artists') is None:
            parse.parseShortTopArtists(sp)
        if session.get('short-artist-genres-all') is None:
            parse.parseTopGenresFromShortArtist(sp)
        genre_count = session['top-genres-from-short-artist']
        basis = 'short-artist'

    return render_template('top_genres.html', counts=genre_count, basis=basis, user=session['user'])

@app.route('/user/top-artists', methods=['GET', 'POST'])
def top_artists():
    auth_manager = spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope, cache_path=session_cache_path())
    if not auth_manager.get_cached_token():
        return redirect('/user')
    sp = spotipy.Spotify(auth_manager=auth_manager)
    artists = []
    basis = None
    counted = False

    if request.method == 'POST' and 'short-term' in request.form:
        if session.get('short-top-artists-name') is None:
            parse.parseShortTopArtistsName(sp)
        artists = session['short-top-artists-name']
        basis = 'short-term'

    if request.method == 'POST' and 'medium-term' in request.form:
        if session.get('medium-top-artists-name') is None:
           parse.parseMediumTopArtistsName(sp)
        artists = session['medium-top-artists-name']
        basis = 'medium-term'

    if request.method == 'POST' and 'long-term' in request.form:
        if session.get('long-top-artists-name') is None:
            parse.parseLongTopArtistsName(sp)
        artists = session['long-top-artists-name']
        basis = 'long-term'

    if request.method == 'POST' and 'saved-library' in request.form:
        if session.get('top-artists-from-library') is None:
            if session.get('saved-library-tracks') is None:
                parse.parseSavedLibraryTracks(sp)
            parse.parseTopArtistsFromSavedLibrary(sp)
        artists = session['top-artists-from-library']
        basis = 'saved-library'
        counted = True

    if request.method == 'POST' and 'all-playlist' in request.form:
        if session.get('top-artists-from-playlist') is None:
            tracks = []
            if session.get('all-playlist-tracks') is None:
                token = auth_manager.get_access_token(as_dict=False)
                parse.parseAllPlaylistTracks(sp, token)
            parse.parseTopArtistFromPlaylist(sp)
        artists = session['top-artists-from-playlist']
        basis = 'all-playlist'
        counted = True

    if request.method == 'POST' and 'combined' in request.form:
        if session.get('combined-library-playlist-tracks') is None:
            token = auth_manager.get_access_token(as_dict=False)
            parse.parseCombinedTracks(sp, token)
        if session.get('combined-track-artist-dict') is None:
            parse.parseCombinedTrackArtistDict()
        if session.get('top-artists-from-combined') is None:
            parse.parseTopArtistsFromCombined()
        artists = session['top-artists-from-combined']
        basis = 'combined'
        counted = True

    return render_template('top_artists.html', counts=artists, basis=basis , counted=counted, user=session['user']) 

@app.route('/user/create-playlist', methods=['GET', 'POST'])
def create_playlists():
    auth_manager = spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope, cache_path=session_cache_path())
    if not auth_manager.get_cached_token():
        return redirect('/user')
    sp = spotipy.Spotify(auth_manager=auth_manager)
    form = SingleInputPlaylistForm()
    message = None

    if request.method == 'POST' and 'track-artist' in request.form:
        if session.get('saved-library-tracks') is None:
            parse.parseSavedLibraryTracks(sp)
        if session.get('library-artists-track-artist-dict') is None:
            parse.parseLibraryTrackArtistDict()
        track_artist_dict = session['library-artists-track-artist-dict']
        artist = form.input.data
        print(form.input.data)
        playlist_name = form.name.data
        print(form.name.data)
        uris = mei.getUrisFromSaved(track_artist_dict, artist)
        mei.createPlaylistFromUris(uris, sp, playlist_name)

    if request.method == 'POST' and 'track-genre' in request.form:
        if session.get('saved-library-tracks') is None:
            parse.parseSavedLibraryTracks(sp)
        if session.get('saved-library-track-genre-dict') is None:
            parse.parseLibraryGenreDict()
        genre = form.input.data
        playlist_name = form.name.data
        uris = mei.getUrisFromSaved(track_genre_dict, genre)
        mei.createPlaylistFromUris(uris, sp, playlist_name)

    if request.method == 'POST' and 'combined-track-artist' in request.form:
        if session.get('combined-library-playlist-tracks') is None:
            token = auth_manager.get_access_token(as_dict=False)
            parse.parseCombinedTracks(sp, token)
        if session.get('combined-track-artist-dict') is None:
            token = auth_manager.get_access_token(as_dict=False)
            parse.parseCombinedTrackArtistDict()
        track_artist_dict = session['combined-track-artist-dict']
        artist = form.input.data
        playlist_name = form.name.data
        uris = mei.getUrisFromSaved(track_artist_dict, artist)
        mei.createPlaylistFromUris(uris, sp, playlist_name)

    if request.method == 'POST' and 'combined-track-genre' in request.form:
        if session.get('combined-library-playlist-tracks') is None:
            token = auth_manager.get_access_token(as_dict=False)
            parse.parseCombinedTracks(sp, token)
        if session.get('combined-track-genre-dict') is None:
            parse.parseCombinedTrackGenreDict(sp)
        track_genre_dict = session['combined-track-genre-dict']
        genre = form.input.data
        playlist_name = form.name.data
        uris = mei.getUrisFromSaved(track_genre_dict, genre)
        mei.createPlaylistFromUris(uris, sp, playlist_name)

    return render_template('create_playlist.html', form=form, user=session['user'])

@app.route('/user/recommendations', methods=['GET', 'POST'])
def get_recommendations():
    auth_manager = spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope, cache_path=session_cache_path())
    if not auth_manager.get_cached_token():
        return redirect('/user')
    sp = spotipy.Spotify(auth_manager=auth_manager)
    form = RecommendationForm()
    message = None
    tabs = None

    if request.method == 'POST' and form.validate() and 'normal' in request.form:
        if session.get('combined-library-playlist-tracks') is None:
            token = auth_manager.get_access_token(as_dict=False)
            parse.parseCombinedTracks(sp, token)
        all_tracks = session['combined-library-playlist-tracks']
        artist_names = form.artists.data.split(",")
        genre_names = form.genres.data.split(",")
        track_names = form.tracks.data.split(",")
        print(artist_names)
        playlist_name = form.name.data
        amount = form.amount.data
        uris = None
        if form.unique.data is True:
            print('UNIQUE')
            uris = mei.getUniqueTrackRecommendationUris(artist_names, genre_names, track_names, all_tracks, amount, sp)
        else:
            print('NOT UNIQUE')
            uris = mei.getTrackRecommendationUris(artist_names, genre_names, track_names, all_tracks, amount, sp)
        if uris is not False:
            uris = list(uris)
            print(len(uris))
            mei.createPlaylistFromUris(uris, sp, playlist_name)
            message = "Playlist '{}' successfully created".format(playlist_name)
        else:
            message = "Recommendations could not be generated: Some artists/tracks may be incompatible"
        

    if request.method == 'POST' and form.validate() and 'tabs' in request.form:
        if session.get('combined-library-playlist-tracks') is None:
            token = auth_manager.get_access_token(as_dict=False)
            parse.parseCombinedTracks(sp, token)
        all_tracks = session['combined-library-playlist-tracks']
        artist_names = form.artists.data.split(",")
        genre_names = form.genres.data.split(",")
        track_names = form.tracks.data.split(",")
        playlist_name = form.name.data
        amount = form.amount.data
        uris = None
        if form.unique.data is True:
            uris, tabs = mei.getUniqueTabTrackRecommendationUris(artist_names, genre_names, track_names, all_tracks, amount, sp)
        else:
            uris, tabs = mei.getTabTrackRecommendationUris(artist_names, genre_names, track_names, all_tracks, amount, sp)
        if uris is not False:
            uris = list(uris)
            print(len(uris))
            mei.createPlaylistFromUris(uris, sp, playlist_name)
            message = "Playlist '{}' successfully created".format(playlist_name)
        else:
            message = "Recommendations could not be generated: Some artists/tracks may be incompatible"

    return render_template('recommendations.html', form=form, message=message, tabs=tabs, user=session['user'])
