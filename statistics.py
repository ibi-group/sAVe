import sqlite3
import json
import time
import collections


# Inserts trip data into database.
def write_trip(
    origin_latitude, origin_longitude, destination_latitude,
    destination_longitude, trips, preferences, time_now, user_id,
    origin, destination
):
    input_dictionary = collections.defaultdict(lambda: 0, locals())
    del input_dictionary["trips"]
    del input_dictionary["preferences"]
    input_dictionary.update(preferences)
    connection = sqlite3.connect('statistics.db')
    with connection:
        cursor = connection.cursor()
        create_trips_table(cursor)
        input_dictionary["trip_id"] = cursor.execute(
                '''SELECT MAX(trip_id) FROM trips'''
        ).fetchone()[0]
        # Getting a single trip_id for all the returned results for a search.
        if (not input_dictionary["trip_id"]):
            input_dictionary["trip_id"] = 1
        else:
            input_dictionary["trip_id"] += 1
        trips["id"] = input_dictionary["trip_id"]
        for trip in trips["trips"]:
            input_dictionary["trip"] = trip
            for leg in trip["legs"]:
                input_dictionary[leg["mode"]] = 1
            cursor.execute(
                    '''INSERT INTO trips (
                            origin_latitude, origin_longitude,
                            destination_latitude, destination_longitude,
                            ada, low_income,
                            senior, student,
                            ada_desert, transit_desert,
                            walk, bike,
                            metro, train,
                            trip_object, time_now,
                            rideshare, user_id,
                            trip_id, origin,
                            destination)
                            VALUES (
                            :origin_latitude, :origin_longitude,
                            :destination_latitude,
                            :destination_longitude,
                            :ada, :low_income,
                            :senior, :student,
                            :ada_desert, :transit_desert,
                            :walk, :bike,
                            :metro, :train,
                            :trip_object, :time_now,
                            :rideshare, :user_id,
                            :trip_id, :origin,
                            :destination)
                    ''', input_dictionary)
            trip["id"] = cursor.lastrowid
        trips["chosen"] = 0
        return True


# Choose a trip by the narrower trip_id, corresponding to ROWID.
def choose_trip(trip_id):
    connection = sqlite3.connect('statistics.db')
    with connection:
        connection.execute(
            '''UPDATE trips SET chosen=1 WHERE ROWID=?''',
            (trip_id,)
        )
    return True


# This is to get the chosen trip by the broader trip_id. Currently has no use.
def get_chosen(trip_id):
    connection = sqlite3.connect('statistics.db')
    # connection.row_factory = sqlite3.Row
    with connection:
        chosen = connection.execute('''SELECT * FROM trips
                                        WHERE chosen=1 AND trip_id=?''',
                                    (trip_id,))
    if not chosen:
        return False
    return chosen[0]


# Made a function for this instead of cluttering every other function with it.
def create_trips_table(cursor):
    query = '''CREATE TABLE IF NOT EXISTS trips (
                    origin TEXT DEFAULT NULL,
                    destination TEXT DEFAULT NULL,
                    origin_latitude TEXT DEFAULT NULL,
                    origin_longitude TEXT DEFAULT NULL,
                    destination_latitude TEXT DEFAULT NULL,
                    destination_longitude TEXT DEFAULT NULL,
                    trip_object BLOB DEFAULT NULL,
                    ada INTEGER DEFAULT 0,
                    low_income INTEGER DEFAULT 0,
                    senior INTEGER DEFAULT 0,
                    student INTEGER DEFAULT 0,
                    time_now TEXT DEFAULT NULL,
                    chosen INTEGER DEFAULT 0,
                    ada_desert INTEGER DEFAULT 0,
                    transit_desert INTEGER DEFAULT 0,
                    walk INTEGER DEFAULT 0,
                    bike INTEGER DEFAULT 0,
                    metro INTEGER DEFAULT 0,
                    train INTEGER DEFAULT 0,
                    trip_id INTEGER DEFAULT 0,
                    rideshare INTEGER DEFAULT 0,
                    user_id INTEGER DEFAULT 0)
            '''
    cursor.execute(query)


# Get the total number of results, and number of trips that have been chosen.
def get_totals():
    connection = sqlite3.connect('statistics.db')
    connection.row_factory = sqlite3.Row
    totals = {}
    with connection:
        cursor = connection.cursor()
        create_trips_table(cursor)
        fetched = cursor.execute('''SELECT COUNT(trip_id),
                                    SUM(chosen) FROM trips''').fetchone()
        return fetched


# Get all stats listed as a dictionary.
def get_trip_statistics():
    connection = sqlite3.connect('statistics.db')
    connection.row_factory = sqlite3.Row
    with connection:
        cursor = connection.cursor()
        create_trips_table(cursor)
        # Select sum because it's easier than writing SELECT all_the_stuff
        # where all_the_stuff = 1 .
        count_fetch = cursor.execute('''SELECT
                                        SUM(ada) as ada,
                                        SUM(student) as student,
                                        SUM(low_income) as low_income,
                                        SUM(senior) as senior,
                                        SUM(ada_desert) as ada_desert,
                                        SUM(transit_desert) as transit_desert,
                                        SUM(walk) as walk,
                                        SUM(bike) as bike,
                                        SUM(metro) as metro,
                                        SUM(train) as train,
                                        SUM(rideshare) as rideshare
                                        FROM trips''').fetchone()
        # If it's empty, return False. This may not be handled on other end.
        if (not count_fetch):
            return False
        return dict(count_fetch)


# Gets a count of a statistic, like ada or transit_desert. statistics is a
# list, so it accepts multiple like ["ada", "transit_desert"]. Then type_ sets
# it as either an OR or AND query.
def get_statistic(statistics, type_):
    connection = sqlite3.connect('statistics.db')
    connection.row_factory = sqlite3.Row
    with connection:
        cursor = connection.cursor()
        create_trips_table(cursor)
        # Will query like "WHERE statistics[0] = 1 type_ statistics[1] = 1".
        # type_ will be AND or OR.
        query = ('''SELECT
                    COUNT(trip_id), SUM(chosen)
                    FROM trips
                    WHERE {} = 1
                ''')
        # Could not think of a better way to do this, really. There's no
        # good way to stick in a dynamic number of variables, unless maybe you
        # just loop through executing once over and over.
        format_string = (" = 1 " + type_ + " ").join(statistics)
        query = query.format(format_string)
        count_fetch = cursor.execute(query).fetchone()
        count_dict = {}
        if (not count_fetch):
            return False
        return count_fetch


# Returns a dictionary of all lat/lon for origins and destinations.
def get_all_latitude_longitude():
    connection = sqlite3.connect('statistics.db')
    connection.row_factory = sqlite3.Row
    with connection:
        create_trips_table(connection)
        locations = connection.execute('''SELECT DISTINCT
                                            origin_latitude,
                                            origin_longitude,
                                            destination_latitude,
                                            destination_longitude
                                            FROM trips''').fetchall()
    return locations


# Returns a dictionary of filtered lat/lon for origins and destinations.
def get_filtered_latitude_longitude(statistics, type_):
    connection = sqlite3.connect('statistics.db')
    connection.row_factory = sqlite3.Row
    with connection:
        create_trips_table(connection)
        query = ('''SELECT DISTINCT
                    origin_latitude,
                    origin_longitude,
                    destination_latitude,
                    destination_longitude
                    FROM trips
                    WHERE {} = 1
                ''')
        # Will query like "WHERE statistics[0] = 1 type_ statistics[1] = 1".
        # type_ will be AND or OR.
        format_string = (" = 1 " + type_ + " ").join(statistics)
        query = query.format(format_string)
        locations = connection.execute(query).fetchall()
    return locations


if __name__ == "__main__":
    # print("hey")
    # write_trip(1,1,1,1,1,1)
    print(get_trip_statistics())
