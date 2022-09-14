# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import datetime
import sys
import dateutil.parser
import babel
from flask import (
    Flask,
    render_template,
    request,
    Response,
    flash,
    redirect,
    url_for,
    abort
)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

from models import Venue, Artist, Show, db
db.init_app(app)
# db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    venue_all = Venue.query.order_by(Venue.id.desc()).limit(10).all()
    artist_all = Artist.query.order_by(Artist.id.desc()).limit(10).all()
    return render_template('pages/home.html', venues=venue_all, artists=artist_all)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    venue_all = Venue.query.with_entities(Venue.city, Venue.state).distinct(Venue.city, Venue.state)
    current_time = datetime.now()
    for ven in venue_all:
        venues_in_city = Venue.query.with_entities(Venue.id, Venue.name).filter_by(city=ven[0]).filter_by(
            state=ven[1])
        v_dic = []
        for venc in venues_in_city:
            sc = Show.query.join(Venue).filter(Show.venue_id == venc.id).filter(Show.start_time > datetime.now()).count()
            v_dic.append({
                "id": venc.id,
                "name": venc.name,
                "num_upcoming_shows": sc
            })
        data.append({"city": ven[0], "state": ven[1], "venues": v_dic})
    return render_template('pages/venues.html', areas=data);


@app.route('/venues/search', methods=['POST'])
def search_venues():
    key = request.form.get('search_term', '')

    query = Venue.query.filter(Venue.name.ilike("%" + key + "%")).all()
    count = Venue.query.filter(Venue.name.ilike("%" + key + "%")).count()
    current_time = datetime.now()
    v_search = []
    for que in query:
        v_search.append({
            "id": que.id,
            "name": que.name,
            "num_upcoming_shows": Show.query.join(Venue).filter_by(venue_id=que.id).filter(
                Show.start_time > current_time).count()
        })

    response = {
        "count": count,
        "data": v_search
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    ven = Venue.query.filter_by(id=venue_id).first()
    if ven is None:
        abort(404)
    all_shows = ven.shows
    current_time = datetime.now()
    past_shows = []
    upcoming_shows = []
    for show in all_shows:
        query = Show.query.join(Artist).with_entities(
            Show.artist_id,
            Artist.name,
            Artist.image_link,
            Show.start_time).filter(Show.venue_id == venue_id).first()
        arr = {
            "artist_id": query[0],
            "artist_name": query[1],
            "artist_image_link": query[2],
            "start_time": format_datetime(str(query[3]))
        }
        if show.start_time > current_time:
            upcoming_shows.append(arr)
        else:
            past_shows.append(arr)
    data = {
        "id": ven.id,
        "name": ven.name,
        "genres": [ven.genres],
        "address": ven.address,
        "city": ven.city,
        "state": ven.state,
        "phone": ven.phone,
        "website_link": ven.website_link,
        "facebook_link": ven.facebook_link,
        "seeking_talent": ven.seeking_talent,
        "seeking_description": ven.seeking_description,
        "image_link": ven.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }
    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    error = False
    seeking_talent = False
    if request.form.get('seeking_talent', 'n') == 'y':
        seeking_talent = True
    try:
        venue = Venue(
            name=request.form.get('name', ''),
            city=request.form.get('city', ''),
            state=request.form.get('state', ''),
            address=request.form.get('address', ''),
            phone=request.form.get('phone', ''),
            image_link=request.form.get('image_link', ''),
            genres=request.form.get('genres', ''),
            facebook_link=request.form.get('facebook_link', ''),
            website_link=request.form.get('website_link', ''),
            seeking_talent=seeking_talent,
            seeking_description=request.form.get('seeking_description', ''),
        )
        form.populate_obj(venue)
        db.session.add(venue)
        db.session.commit()
    except ValueError as e:
        print(e)
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    else:
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>/delete', methods=['GET'])
def delete_venue(venue_id):
    error = False
    name = venue_id
    try:
        venue = Venue.query.filter_by(id=venue_id).first()
        if venue is None:
            abort(404)
        name = venue.name
        db.session.delete(venue)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' + name + ' could not be deleted.')
    else:
        flash('Venue ' + name + ' was successfully deleted!')

    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return redirect(url_for('index'))


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = []
    artist_all = Artist.query.all()
    for artist in artist_all:
        data.append({
            "id": artist.id,
            "name": artist.name
        })
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    keyword = request.form.get('search_term', '')

    query = Artist.query.filter(Artist.name.ilike("%" + keyword + "%")).all()
    count = Artist.query.filter(Artist.name.ilike("%" + keyword + "%")).count()
    current_time = datetime.now()
    arts = []
    for a in query:
        arts.append({
            "id": a.id,
            "name": a.name,
            "num_upcoming_shows": Show.query.filter_by(artist_id=a.id).filter(Show.start_time > current_time).count()
        })

    response = {
        "count": count,
        "data": arts
    }
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    art = Artist.query.filter_by(id=artist_id).first()
    if art is None:
        abort(404)
    all_shows = art.shows
    current_time = datetime.now()
    past_shows = []
    upcoming_shows = []
    for show in all_shows:
        query = Show.query.join(Venue).with_entities(
            Show.artist_id,
            Venue.name,
            Venue.image_link,
            Show.start_time
        ).filter(Show.artist_id == artist_id).first()
        arr = {
            "venue_id": query[0],
            "venue_name": query[1],
            "venue_image_link": query[2],
            "start_time": format_datetime(str(query[3]))
        }
        if show.start_time > current_time:
            upcoming_shows.append(arr)
        else:
            past_shows.append(arr)
    data = {
        "id": art.id,
        "name": art.name,
        "genres": [art.genres],
        "city": art.city,
        "state": art.state,
        "phone": art.phone,
        "website_link": art.website_link,
        "facebook_link": art.facebook_link,
        "seeking_venue": art.seeking_venue,
        "seeking_description": art.seeking_description,
        "image_link": art.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    art_data = Artist.query.filter_by(id=artist_id).first()
    if art_data is None:
        abort(404)
    artist = {
        "id": art_data.id,
        "name": art_data.name,
        "genres": art_data.genres,
        "city": art_data.city,
        "state": art_data.state,
        "phone": art_data.phone,
        "website_link": art_data.website_link,
        "facebook_link": art_data.facebook_link,
        "seeking_venue": art_data.seeking_venue,
        "seeking_description": art_data.seeking_description,
        "image_link": art_data.image_link
    }
    form = ArtistForm()
    form.name.data = art_data.name
    form.genres.data = art_data.genres
    form.city.data = art_data.city
    form.state.data = art_data.state
    form.phone.data = art_data.phone
    form.website_link.data = art_data.website_link
    form.facebook_link.data = art_data.facebook_link
    form.seeking_venue.data = art_data.seeking_venue
    form.seeking_description.data = art_data.seeking_description
    form.image_link.data = art_data.image_link
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    error = False
    seeking_venue = False
    if request.form.get('seeking_venue', 'n') == 'y':
        seeking_venue = True
    try:
        artist = Artist.query.filter_by(id=artist_id).first()
        artist.name = request.form.get('name', '')
        artist.genres = request.form.get('genres', '')
        artist.city = request.form.get('city', '')
        artist.state = request.form.get('state', '')
        artist.phone = request.form.get('phone', '')
        artist.website_link = request.form.get('website_link', '')
        artist.facebook_link = request.form.get('facebook_link', '')
        artist.seeking_venue = seeking_venue
        artist.seeking_description = request.form.get('seeking_description', '')
        artist.image_link = request.form.get('image_link', '')
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')
    else:
        flash('Artist ' + request.form['name'] + ' was successfully updated!')

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    data = Venue.query.filter_by(id=venue_id).first()
    if data is None:
        abort(404)
    venue = {
        "id": data.id,
        "name": data.name,
        "genres": data.genres,
        "address": data.address,
        "city": data.city,
        "state": data.state,
        "phone": data.phone,
        "website_link": data.website_link,
        "facebook_link": data.facebook_link,
        "seeking_talent": data.seeking_talent,
        "seeking_description": data.seeking_description,
        "image_link": data.image_link
    }
    form.name.data = data.name
    form.genres.data = data.genres
    form.address.data = data.address
    form.city.data = data.city
    form.state.data = data.state
    form.phone.data = data.phone
    form.website_link.data = data.website_link
    form.facebook_link.data = data.facebook_link
    form.seeking_talent.data = data.seeking_talent
    form.seeking_description.data = data.seeking_description
    form.image_link.data = data.image_link
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(ven_id):
    error = False
    seeking_talent = False
    if request.form.get('seeking_talent', 'n') == 'y':
        seeking_talent = True
    try:
        ven = Venue.query.filter_by(id=ven_id).first()
        ven.name = request.form.get('name', '')
        ven.genres = request.form.get('genres', '')
        ven.address = request.form.get('address', '')
        ven.city = request.form.get('city', '')
        ven.state = request.form.get('state', '')
        ven.phone = request.form.get('phone', '')
        ven.website_link = request.form.get('website_link', '')
        ven.facebook_link = request.form.get('facebook_link', '')
        ven.seeking_talent = seeking_talent
        ven.seeking_description = request.form.get('seeking_description', '')
        ven.image_link = request.form.get('image_link', '')
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')
    else:
        flash('Venue ' + request.form['name'] + ' was successfully updated!')

    return redirect(url_for('show_venue', venue_id=ven_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm(request.form)
    error = False
    seeking_venue = False
    if request.form.get('seeking_venue', 'n') == 'y':
        seeking_venue = True
    try:
        artist = Artist(
            name=request.form.get('name', ''),
            city=request.form.get('city', ''),
            state=request.form.get('state', ''),
            phone=request.form.get('phone', ''),
            image_link=request.form.get('image_link', ''),
            genres=request.form.get('genres', ''),
            facebook_link=request.form.get('facebook_link', ''),
            website_link=request.form.get('website_link', ''),
            seeking_venue=seeking_venue,
            seeking_description=request.form.get('seeking_description', ''),
        )
        form.populate_obj(artist)
        db.session.add(artist)
        db.session.commit()
    except ValueError as e:
        print(e)
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    else:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    show_all = Show.query.order_by(Show.start_time.asc()).all()
    data = []
    for show in show_all:
        data.append({
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": format_datetime(str(show.start_time))
        })
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form)
    error = False
    try:
        show = Show(start_time=request.form.get('start_time', datetime.now()))
        artist = Artist.query.filter_by(id=request.form.get('artist_id', '')).first()
        venue = Venue.query.filter_by(id=request.form.get('venue_id', '')).first()
        show.artist = artist
        show.venue = venue
        form.populate_obj(show)
        db.session.add(show)
        db.session.commit()
    except ValueError as e:
        print(e)
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Show could not be listed.')
    else:
        flash('Show was successfully listed!')
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
