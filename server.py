#!/usr/bin/env python

"""
Columbia's COMS W4111.003 Introduction to Databases
Example Webserver

To run locally:

    python server.py

Go to http://localhost:8111 in your browser.

A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
from dotenv import load_dotenv
import json
import datetime
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
# XXX: The URI should be in the format of:
#     postgresql://USER:PASSWORD@104.196.152.219/proj1part2
# For example, if you had username biliris and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://biliris:foobar@104.196.152.219/proj1part2"
load_dotenv()
DATABASEURI = os.getenv("DATABASE_ADDRESS")

# This line creates a database engine that knows how to connect to the URI above.
engine = create_engine(DATABASEURI)


@app.before_request
def before_request():
    """
    This function is run at the beginning of every web request 
    (every time you enter an address in the web browser).
    We use it to setup a database connection that can be used throughout the request.

    The variable g is globally accessible.
    """
    try:
        g.conn = engine.connect()
    except:
        print("uh oh, problem connecting to database")
        import traceback
        traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(exception):
    """
    At the end of the web request, this makes sure to close the database connection.
    If you don't, the database could run out of memory!
    """
    try:
        g.conn.close()
    except Exception as e:
        pass


@app.route('/')
def index():
    """
    request is a special object that Flask provides to access web request information:

    request.method:   "GET" or "POST"
    request.form:     if the browser submitted a form, this contains the data in the form
    request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

    See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
    """

    # DEBUG: this is debugging code to see what request looks like
    print(request.args)
    names_args = request.args.getlist('firstNames[]')
    park_zone_args = request.args.getlist('parkZones[]')
    subway_args = request.args.getlist('entranceZones[]')
    sounds_args = request.args.getlist('squirrelSounds[]')
    weather_args = request.args.getlist('weather[]')
    selected_dropdowns = {'names': names_args, 'parks': park_zone_args,
                          'subways': subway_args, 'sounds': sounds_args, 'weather': weather_args}

    query = ("SELECT spot.zoneid, spot.dateofspotting, spot.location, s.color, s.age, s.firstname, park.zonename, sound.name, subway.name, subway.line " +
             "FROM spotted_at spot " +
             "JOIN squirrel s ON s.squirrelid=spot.squirrelid " +
             "JOIN park_zone park ON park.zoneid=spot.zoneid " +
             "JOIN subway_entrance subway ON subway.entranceid=spot.entranceid "
             "LEFT JOIN made_sound ON made_sound.squirrelid=s.squirrelid " +
             "LEFT JOIN squirrel_sound sound ON made_sound.soundid=sound.soundid "
             "LEFT JOIN weather_report w ON w.date=spot.dateofspotting ")

    query += "WHERE "
    if names_args:
        query += "s.firstname IN (" + ', '.join(
            ["'" + name.replace("'", "''") + "'" for name in names_args]) + ") AND "
    if park_zone_args:
        query += "park.zonename IN (" + ', '.join(
            ["'" + zone.replace("'", "''") + "'" for zone in park_zone_args]) + ") AND "
    if subway_args:
        query += "subway.name IN (" + ', '.join(
            ["'" + subway.replace("'", "''") + "'" for subway in subway_args]) + ") AND "
    if sounds_args:
        if 'None' in sounds_args:
            query += "(s.squirrelid NOT IN (SELECT squirrelid FROM made_sound) OR sound.name IN (" + \
                ','.join(["'" + sound + "'" for sound in sounds_args]
                         ) + ")) AND "
        else:
            query += "sound.name IN (" + ','.join(
                ["'" + sound + "'" for sound in sounds_args]) + ") AND "
    if weather_args:
        query += "w.weather IN (" + ','.join(
            ["'" + weather + "'" for weather in weather_args]) + ") AND "

    if query[-4:] == 'AND ':
        query = query[:-4]
    else:
        query = query[:-6]

    query += "ORDER BY park.zonename "

    cursor = g.conn.execute(query)

    spottings = []
    for result in cursor:
        subway = result[8] + " (Lines: " + result[9] + ")"
        spottings.append({'squirrelid': result[0], 'dateofspotting': result[1].isoformat(),
                         'location': result[2], 'color': str(result[3]), 'age': str(result[4]), 'firstname': str(result[5]), 'zone': str(result[6]), 'sound': str(result[7]), 'subway': str(subway)})
    cursor.close()
    # Sanitizing
    for spotting in spottings:
        if spotting["color"] is None:
            spotting["color"] = "Unknown"
        if spotting["age"] is None:
            spotting["age"] = "Unknown"
        if spotting["sound"] is None:
            spotting["sound"] = "None"

    # Get the concession details
    cursor = g.conn.execute("SELECT c.name, c.location, c.type " +
                            "FROM concession c " +
                            "JOIN park_zone park ON park.zoneid=c.zoneid")
    concessions = []
    for result in cursor:
        concessions.append(
            {'name': str(result[0]), 'location': result[1], 'type': str(result[2])})
    cursor.close()

    # Get dropdown values

    cursor = g.conn.execute("SELECT DISTINCT firstname FROM squirrel")
    names = []
    for result in cursor:
        names.append(result['firstname'])
    cursor.close()

    cursor = g.conn.execute("SELECT DISTINCT zonename FROM park_zone")
    zone_names = []
    for result in cursor:
        zone_names.append(result['zonename'])
    cursor.close()

    sounds = ['kuk', 'quaa', 'moan', 'None']
    weather = ['Snowy', 'Rainy', 'Sunny']

    cursor = g.conn.execute("SELECT DISTINCT subway.name " +
                            "FROM spotted_at spot " +
                            "JOIN subway_entrance subway ON subway.entranceid=spot.entranceid " +
                            "ORDER BY subway.name")
    entrance_names = []
    for result in cursor:
        entrance_names.append(result['name'])
    cursor.close()

    cursor = g.conn.execute("SELECT name, sound, meaning FROM squirrel_sound")
    squirrel_sounds = []
    for result in cursor:
        squirrel_sounds.append(
            {'name': result[0], 'sound': result[1], 'meaning': result[2]})
    cursor.close()

    context = dict(names=names,
                   zone_names=zone_names,
                   entrance_names=entrance_names,
                   spottings=spottings,
                   selected_dropdowns=selected_dropdowns,
                   squirrel_sounds=squirrel_sounds,
                   sounds=sounds,
                   weather=weather,
                   concessions=concessions)

    # render_template looks in the templates/ folder for files.
    return render_template("map.html", **context)


if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        """
        This function handles command line parameters.
        Run the server using:

            python server.py

        Show the help text using:

            python server.py --help

        """

        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()
