# Docs on session basics
# https://docs.sqlalchemy.org/en/13/orm/session_basics.html


# Now that you have completed your initial analysis, design a Flask API
# based on the queries that you have just developed.

import numpy as np
import os
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy import create_engine, func
import datetime as dt
from flask import Flask, jsonify


#################################################
# Database Setup
#################################################
engine = create_engine("sqlite:///Resources/hawaii.sqlite")

# reflect an existing database into a new model
Base = automap_base()
Base.prepare(engine, reflect=True)

# Save reference to the table
Measurement = Base.classes.measurement
Station = Base.classes.station

#################################################
# Flask Setup
#################################################
app = Flask(__name__)

#################################################
# Flask Routes
#################################################
# Use Flask to create your routes.

# Routes

# /
# Home page. List all routes that are available.
@app.route("/")
def welcome():
    """List all available api routes."""
    return (
        f"<h3>Available Routes:</h3>"
        f"<h4>Precipitation (all dates available in the database):</h4>"
        f"/api/v1.0/precipitation<br/><br/>"
        f"<h4>Stations:</h4>"
        f"/api/v1.0/stations<br/><br/>"
        f"<h4>Temperature Observations (last 12 months of dates available in the database):</h4>"
        f"/api/v1.0/tobs<br/><br/>"
        f"<h4>Minimum, average, and the max temperature for a given start:</h3>"
        f"/api/v1.0/start<br/>"
        f"<h4>Minimum, average, and the max temperature for a given start or start-end range:</h3>"
        f"/api/v1.0/start/end<br/>"
    )


# /api/v1.0/precipitation
# Convert the query results to a dictionary using date as the key and prcp as the value.
# Return the JSON representation of your dictionary.
@app.route("/api/v1.0/precipitation")
def precipitation():
    """Return a list of all precipitation measurments"""

    # open the session to start the communication with the database
    session = Session(engine)

    # Retrieve the most recent meas data
    date_last_meas_str = session.query(func.max(Measurement.date))

    # Convert the data from string to datetime
    date_last_meas_object = dt.datetime.strptime(
        date_last_meas_str.first()[0], "%Y-%m-%d"
    ).date()

    # Create a query data interval
    query_date = date_last_meas_object - dt.timedelta(days=365)

    # Query the database based on the target date (last 365 days)
    results = (
        session.query(Measurement.date, Measurement.prcp)
        .filter(Measurement.date > query_date)
        .all()
    )

    # close the session to end the communication with the database
    session.close()

    # Create a dictionary from the row data and append to a list of all_stations
    all_precipitation = []
    for meas in results:
        # meas_dict = {str(meas.date): meas.prcp}
        meas_dict = {(meas.date): meas.prcp}
        all_precipitation.append(meas_dict)

    return jsonify(all_precipitation)


# /api/v1.0/stations
# Return a JSON list of stations from the dataset.
@app.route("/api/v1.0/stations")
def stations():
    """Return a list of all stations"""

    # open the session to start the communication with the database
    session = Session(engine)

    # Query all precipitation measurments
    results = session.query(
        Station.id,
        Station.station,
        Station.name,
        Station.latitude,
        Station.longitude,
        Station.elevation,
    ).all()

    # close the session to end the communication with the database
    session.close()

    # Create a dictionary from the row data and append to a list of all_stations
    all_stations = []
    for stat in results:
        station_dict = {}
        station_dict["Id"] = stat.id
        station_dict["Station"] = stat.station
        station_dict["Name"] = stat.name
        station_dict["Latitude"] = stat.latitude
        station_dict["Longitude"] = stat.longitude
        station_dict["Elevation"] = stat.elevation
        all_stations.append(station_dict)

    return jsonify(all_stations)


# /api/v1.0/tobs
# Query the dates and temperature observations of the most active station for the last year of data.
# Return a JSON list of temperature observations (TOBS) for the previous year.
@app.route("/api/v1.0/tobs")
def tobs():
    """Return a list of all tobs"""

    # open the session to start the communication with the database
    session = Session(engine)

    # Retrieve the most recent meas data
    date_last_meas_str = session.query(func.max(Measurement.date))

    # Convert the data from string to datetime
    date_last_meas_object = dt.datetime.strptime(
        date_last_meas_str.first()[0], "%Y-%m-%d"
    ).date()

    # Create a query data interval
    query_date = date_last_meas_object - dt.timedelta(days=365)

    # What are the most active stations? (i.e. what stations have the most rows)?
    # List the stations and the counts in descending order.
    most_active_stations = (
        session.query(Station.station, func.count(Station.station))
        .filter(Measurement.station == Station.station)
        .group_by(Station.station)
        .order_by(func.count(Station.station).desc())
        .all()
    )

    # Using the station id from the previous query the temperature recorded
    most_active_station_id = most_active_stations[0][0]

    results = (
        session.query(Measurement.date, Measurement.tobs)
        .filter(Measurement.date > query_date)
        .filter(Measurement.station == most_active_station_id)
        .all()
    )

    # close the session to end the communication with the database
    session.close()

    # Create a dictionary from the row data and append to a list of all_stations
    all_tobs = []
    for tob in results:
        tob_dict = {}
        tob_dict["Date"] = tob.date
        tob_dict["Temperature"] = tob.tobs
        all_tobs.append(tob_dict)

    return jsonify(all_tobs)


# /api/v1.0/<start> and /api/v1.0/<start>/<end>
# Return a JSON list of the minimum temperature, the average temperature,
# and the max temperature for a given start or start-end range.
# When given the start only, calculate TMIN, TAVG, and TMAX for all dates
# greater than and equal to the start date.
@app.route("/api/v1.0/<start_date>")
def tobs_from_date(start_date):
    """Return a JSON list of the minimum temperature, the average temperature, 
    and the max temperature for a given start data on."""

    # open the session to start the communication with the database
    session = Session(engine)

    # This function called `calc_temps_mod` will accept start date and end date in the format '%Y-%m-%d'
    # and return the minimum, average, and maximum temperatures for that range of dates
    # When given the start only, calculate TMIN, TAVG, and TMAX for all dates greater
    # than and equal to the start date.
    def calc_temps_mod(start_date, end_date=0):
        """TMIN, TAVG, and TMAX for a list of dates.
        
        Args:
            start_date (string): A date string in the format %Y-%m-%d
            end_date (string): A date string in the format %Y-%m-%d
            
        Returns:
            TMIN, TAVE, and TMAX
        """
        if end_date == 0:
            return (
                session.query(
                    func.min(Measurement.tobs),
                    func.avg(Measurement.tobs),
                    func.max(Measurement.tobs),
                )
                .filter(Measurement.date >= start_date)
                .all()
            )
        else:
            return (
                session.query(
                    func.min(Measurement.tobs),
                    func.avg(Measurement.tobs),
                    func.max(Measurement.tobs),
                )
                .filter(Measurement.date >= start_date)
                .filter(Measurement.date <= end_date)
                .all()
            )

    temperatures = calc_temps_mod(start_date)

    # close the session to end the communication with the database
    session.close()

    return jsonify(temperatures)


# /api/v1.0/<start> and /api/v1.0/<start>/<end>
# Return a JSON list of the minimum temperature, the average temperature,
# and the max temperature for a given start or start-end range.
# When given the start and the end date, calculate the TMIN, TAVG, and TMAX
# for dates between the start and end date inclusive.
@app.route("/api/v1.0/<start_date>/<end_date>")
def tobs_from_date_to_date(start_date, end_date):
    """Return a JSON list of the minimum temperature, the average temperature, 
    and the max temperature for a given start data on."""

    # open the session to start the communication with the database
    session = Session(engine)

    # This function called `calc_temps_mod` will accept start date and end date in the format '%Y-%m-%d'
    # and return the minimum, average, and maximum temperatures for that range of dates
    # When given the start only, calculate TMIN, TAVG, and TMAX for all dates greater
    # than and equal to the start date.
    def calc_temps_mod(start_date, end_date=0):
        """TMIN, TAVG, and TMAX for a list of dates.
        
        Args:
            start_date (string): A date string in the format %Y-%m-%d
            end_date (string): A date string in the format %Y-%m-%d
            
        Returns:
            TMIN, TAVE, and TMAX
        """
        if end_date == 0:
            return (
                session.query(
                    func.min(Measurement.tobs),
                    func.avg(Measurement.tobs),
                    func.max(Measurement.tobs),
                )
                .filter(Measurement.date >= start_date)
                .all()
            )
        else:
            return (
                session.query(
                    func.min(Measurement.tobs),
                    func.avg(Measurement.tobs),
                    func.max(Measurement.tobs),
                )
                .filter(Measurement.date >= start_date)
                .filter(Measurement.date <= end_date)
                .all()
            )

    temperatures = calc_temps_mod(start_date, end_date)

    # close the session to end the communication with the database
    session.close()

    return jsonify(temperatures)


if __name__ == "__main__":
    app.run(debug=True)
