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
import json
import datetime
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@104.196.152.219/proj1part2
#
# For example, if you had username biliris and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://biliris:foobar@104.196.152.219/proj1part2"

DATABASEURI = "postgresql://er3074:squirrels@35.196.73.133/proj1part2"

# This line creates a database engine that knows how to connect to the URI above.
engine = create_engine(DATABASEURI)

# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.

'''engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")'''


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


# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request

# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:

#       @app.route("/foobar/", methods=["POST", "GET"])

# PROTIP: (the trailing / in the path is important)
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
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

    query = ("SELECT spot.zoneid, spot.dateofspotting, spot.location, s.color, s.age, s.firstname, park.zonename, sound.name " +
            "FROM spotted_at spot " +
            "JOIN squirrel s ON s.squirrelid=spot.squirrelid " +
            "JOIN park_zone park ON park.zoneid=spot.zoneid " +
            "JOIN subway_entrance subway ON subway.entranceid=spot.entranceid "
            "LEFT JOIN made_sound ON made_sound.squirrelid=s.squirrelid " +
            "LEFT JOIN squirrel_sound sound ON made_sound.soundid=sound.soundid ")

    query += "WHERE "
    if names_args:
      query += "s.firstname IN (" + ', '.join(["'" + name + "'" for name in names_args]) + ") AND "
    if park_zone_args:
      query += "park.zonename IN (" + ', '.join(["'" + zone + "'" for zone in park_zone_args]) + ") AND "
    if subway_args:
      query += "subway.name IN (" + ', '.join(["'" + subway + "'" for subway in subway_args]) + ") AND "

    if query[-4:] == 'AND ':
      query = query[:-4]
    else:
      query = query[:-6]

    query += "ORDER BY park.zonename"

    cursor = g.conn.execute(query)
    
    # cursor = g.conn.execute("SELECT spot.zoneid, spot.dateofspotting, spot.location, s.color, s.age, s.firstname, park.zonename, sound.name " +
    #                         "FROM spotted_at spot " +
    #                         "JOIN squirrel s ON s.squirrelid=spot.squirrelid " +
    #                         "JOIN park_zone park ON park.zoneid=spot.zoneid " +
    #                         "LEFT JOIN made_sound ON made_sound.squirrelid=s.squirrelid " +
    #                         "LEFT JOIN squirrel_sound sound ON made_sound.soundid=sound.soundid " +
    #                         "ORDER BY park.zonename")
    spottings = []
    for result in cursor:
        spottings.append({'squirrelid': result[0], 'dateofspotting': result[1].isoformat(),
                         'location': result[2], 'color': result[3], 'age': result[4], 'firstname': result[5], 'zone': result[6], 'sound': result[7]})
    cursor.close()
    # Sanitizing
    for spotting in spottings:
      if spotting["color"] is None:
        spotting["color"] = "Unknown"
      if spotting["age"] is None:
        spotting["age"] = "Unknown"
      if spotting["sound"] is None:
        spotting["sound"] = "None"

    # get dropdown values

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

    cursor = g.conn.execute("SELECT DISTINCT name FROM subway_entrance")
    entrance_names = []
    for result in cursor:
        entrance_names.append(result['name'])
    cursor.close()

    #
    # example of a database query
    #
    #cursor = g.conn.execute("SELECT firstname FROM squirrel")
    #names = []
    # for result in cursor:
    #  names.append(result['firstname'])  # can also be accessed using result[0]
    # cursor.close()

    #
    # Flask uses Jinja templates, which is an extension to HTML where you can
    # pass data to a template and dynamically generate HTML based on the data
    # (you can think of it as simple PHP)
    # documentation: https://realpython.com/blog/python/primer-on-jinja-templating/
    #
    # You can see an example template in templates/index.html
    #
    # context are the variables that are passed to the template.
    # for example, "data" key in the context variable defined below will be
    # accessible as a variable in index.html:
    #
    #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
    #     <div>{{data}}</div>
    #
    #     # creates a <div> tag for each element in data
    #     # will print:
    #     #
    #     #   <div>grace hopper</div>
    #     #   <div>alan turing</div>
    #     #   <div>ada lovelace</div>
    #     #
    #     {% for n in data %}
    #     <div>{{n}}</div>
    #     {% endfor %}
    #

    context = dict(names=names,zone_names=zone_names,
                   entrance_names=entrance_names, spottings=spottings)

    #
    # render_template looks in the templates/ folder for files.
    # for example, the below file reads template/index.html
    #
    return render_template("map.html", **context)

#
# This is an example of a different path.  You can see it at:
#
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#


@app.route('/another')
def another():
    return render_template("another.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    g.conn.execute('INSERT INTO test VALUES (NULL, ?)', name)
    return redirect('/')


@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()


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
