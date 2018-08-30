import requests
import xmltodict
import statistics
import json
import time
import csv
import collections
import vincenty
from datetime import datetime
from dateutil import relativedelta
import dateutil.parser
from math import cos, asin, sqrt
from google.transit import gtfs_realtime_pb2
from protobuf_to_dict import protobuf_to_dict

# This is a list of every feed_id attached to MTA subway line
FEED_ID = {
    "1": "1", "2": "1", "3": "1", "4": "1", "5": "1", "6": "1",
    "A": "26", "C": "26", "E": "26", "H": "26",
    "N": "16", "Q": "16", "R": "16", "W": "16",
    "B": "21", "D": "21", "F": "21", "M": "21",
    "L": "2",
    "G": "31",
    "J": "36", "Z": "36",
    "7": "51",
}


# This function does coord_time-time_now. Returns a relativedelta. Not used.
def time_difference(coord_time, time_now):
    time1 = parser.isoparse(coord_time)
    time2 = parser.isoparse(time_now)
    tz = time1.tzinfo
    time1 = time1.replace(tz=None)
    return relativedelta.relativedelta(time1, time2)


# Returns a relativedelta of the given time_-time.time(). Not used
def time_from_now(time_):
    # time1 = datetime.now()
    time1 = datetime.fromtimestamp(time.time())
    time2 = datetime.fromtimestamp(time_)
    # tz = time1.tzinfo
    # time1 = time1.replace(tz=None)
    return relativedelta.relativedelta(time2, time1)


# Puts together the trip object, with directions, and realtime, and calculates
# any changes.
def get_directions(origin, destination, radius, preferences, user_id):
    # Dictionary to store the changes made to trip.
    changes = collections.defaultdict(lambda: 0)
    origin_latitude, origin_longitude = \
        get_location_coordinates(origin)
    destination_latitude, destination_longitude = \
        get_location_coordinates(destination)
    if (not (destination_latitude and origin_latitude)):
        return (False, False)
    # Nearest subways.
    origin_subway = nearest_subway(origin_latitude, origin_longitude)
    destination_subway = \
        nearest_subway(destination_latitude, destination_longitude)
    # The final identifier means the latitude and longitude that will be
    # given to Coord. The rest will be filled in (by rideshares).
    final_origin_latitude = origin_latitude
    final_origin_longitude = origin_longitude
    final_destination_latitude = destination_latitude
    final_destination_longitude = destination_longitude
    # Checks for nearby bikes and subways.
    if (not is_transit_near(
            origin_latitude, origin_longitude, radius, origin_subway
    )):
        # Start at subways instead and designate transit_desert.
        final_origin_latitude = origin_subway[0]["GTFS Latitude"]
        final_origin_longitude = origin_subway[0]["GTFS Longitude"]
        changes["transit_desert"] = 1
    if (not is_transit_near(
        destination_latitude, destination_longitude, radius, destination_subway
    )):
        final_destination_latitude = destination_subway[0]["GTFS Latitude"]
        final_destination_longitude = destination_subway[0]["GTFS Longitude"]
        changes["transit_desert"] = 1
    if preferences["ada"]:
        origin_subway = ada_list(origin_subway)
        destination_subway = ada_list(destination_subway)
        # Start at subways instead.
        final_origin_latitude = origin_subway[0]["GTFS Latitude"]
        final_origin_longitude = origin_subway[0]["GTFS Longitude"]
        final_destination_latitude = destination_subway[0]["GTFS Latitude"]
        final_destination_longitude = destination_subway[0]["GTFS Longitude"]
        changes["ada"] = 1
        if (
            (not is_subway_near(origin_subway, radius)) or
            (not is_subway_near(destination_subway, radius))
        ):
            changes["ada_desert"] = 1
        # Send final coordinates to Coord.
    trip = get_coord_directions(
        final_origin_latitude, final_origin_longitude,
        final_destination_latitude, final_destination_longitude,
        preferences["ada"]
    )
    # If there's been a change, a rideshare needs to be added.
    if (
        (final_origin_latitude != origin_latitude) or
        (final_origin_longitude != origin_longitude)
    ):
        add_ride_share(trip)
    if (
        (final_destination_latitude != destination_latitude) or
        (final_destination_longitude != destination_longitude)
    ):
        add_ride_share(trip, True)
    # Align preferences with trip changes.
    for preference, value in preferences.items():
        if preference == "ada":
            continue
        if value:
            if preference == "student":
                changes["student"] = 1
            elif preference == "income":
                if (value <= 50000):
                    changes["low_income"] = 1
            elif preference == "senior":
                changes["senior"] = 1
    time_now = time.asctime()
    # Write trip to database.
    statistics.write_trip(
        origin_latitude, origin_longitude, destination_latitude,
        destination_longitude, trip,
        changes, time_now, user_id, origin, destination
    )
    # Add subway real time to trip.
    try:
        add_real_time(trip)
    # Specifically a network error, or error accessing a dictionary.
    # Implement when possible.
    except:
        pass
    return (trip, changes)


# Checks if there is transit like a bike or bus within the radius.
# Accepts a list of subway stations, as returned by nearest_subway.
def is_transit_near(lat, lon, radius, nearSubway):
    bikeNear = is_bike_near(lat, lon, radius)
    subwayNear = is_subway_near(nearSubway, radius)
    return (bikeNear or subwayNear)


# Adds a rideshare to the trip, defaults to the front of the trip.
def add_ride_share(d, back=False):
    trips = d["trips"]
    newLeg = {"mode": "rideshare"}
    for obj in trips:
        # The object is being edited in-place, so this ensures it leaves the
        # places where a rideshare was already added alone. I think.
        if (
            (len(obj["legs"]) == 1) and
            (obj["legs"][0]["mode"] == "rideshare")
        ):
            continue
        if back:
            # Pop off walking from the back, that's what will be replaced.
            while (obj["legs"] and (obj["legs"][-1]["mode"] in ["walk"])):
                obj["legs"].pop()
            if obj["legs"]:
                newLeg["end"] = obj["legs"][-1]["station_end"]["name"]
                # Add a time for ridshares if they come at the end of a trip.
                start_time = dateutil.parser.parse(
                    obj["legs"][-1]["statistics"]["end_time"]
                ).replace(tzinfo=None)
                time_now = datetime.now()
                newLeg["start_time"] = relativedelta.relativedelta(
                    start_time, time_now
                ).minutes
                newLeg["geometry"] = {"coordinates": []}
                newLeg["geometry"]["coordinates"].append(
                    obj["legs"][-1]["geometry"]["coordinates"][-1])
                # geometry": {
                #     "coordinates": [
            obj["legs"] = obj["legs"] + [newLeg]
        else:
            while (obj["legs"] and (obj["legs"][0]["mode"] in ["walk"])):
                obj["legs"].pop(0)
            if obj["legs"]:
                newLeg["start"] = obj["legs"][0]["station_start"]["name"]
                newLeg["geometry"] = {"coordinates": []}
                newLeg["geometry"]["coordinates"].append(
                    obj["legs"][0]["geometry"]["coordinates"][0])
            obj["legs"] = [newLeg] + obj["legs"]


# Uses Nominatum to get coordinates based on address.
def get_location_coordinates(address):
    with open("secret.json") as f:
        nomkey = json.load(f)["mapquest"]
    nomload = {}
    nomUrl = "http://open.mapquestapi.com/nominatim/v1/search.php?"
    nomload["key"] = nomkey
    nomload["format"] = "json"
    nomload["q"] = address
    nomload["addressdetails"] = 0
    nomload["limit"] = 1
    headers = {
        'User-Agent': 'User Agent for Transit App',
        'From': 'nathalie.waelbroeck@ibigroup.com'
    }
    nomr = requests.get(nomUrl, params=nomload)
    if nomr:
        res = nomr.json()
        if res and (len(res) > 0):
            res = res[0]
            lat = res["lat"]
            lon = res["lon"]
            # time.sleep(1)
            return (lat, lon)
    return (False, False)


# Uses coord to get trip routing instructions.
def get_coord_directions(
        origin_latitude, origin_longitude, destination_latitude,
        destination_longitude, accessible
):
    coordkey = ""
    with open("secret.json") as f:
        coordkey = json.load(f)["coord"]
    coordload = {"access_key": coordkey}
    coordUrl = "https://api.coord.co/v1/routing/route?"
    coordload["origin_latitude"] = origin_latitude
    coordload["origin_longitude"] = origin_longitude
    coordload["destination_latitude"] = destination_latitude
    coordload["destination_longitude"] = destination_longitude
    coordload["modes"] = "metro"
    # Bikes only if not ada.
    if (not accessible):
        coordload["modes"] += ",bike"
    coordr = requests.get(coordUrl, params=coordload)
    return coordr.json()


# Removes geometry from coord for nicer debugging.
def remove_geometry(d):
    trips = d["trips"]
    for obj in trips:
        for obj2 in obj["legs"]:
            obj2["geometry"] = ""
            # obj2["statistics"]["duration_s"]/=60
        # obj["statistics"]["duration_s"]/=60


# Uses coord to check how far the nearest bike station is. Coord accepts a
# radius, so it's easy.
def is_bike_near(lat, lon, km):
    coordkey = ""
    with open("secret.json") as f:
        coordkey = json.load(f)["coord"]
    coordload = {"access_key": coordkey}
    coordUrl = "https://api.coord.co/v1/bike/location?"
    coordload["latitude"] = lat
    coordload["longitude"] = lon
    coordload["radius_km"] = km
    coordr = requests.get(coordUrl, params=coordload)
    d = coordr.json()
    return d["features"] is not None


# Accepts list of subways as given by nearest_subway.
def is_subway_near(L, dist):
    ret = [item for item in L if item["dist"] <= dist]
    return ret


# Uses the vincenty formula to find the distance between given point and all
# subway stations. Returns a list of subway stations sorted by distance.
def nearest_subway(lat, lon):
    L = []
    index = 0
    ref = False
    with open("stations.csv") as f:
        # Hasty implementation of csv.DictReader. Will save some lines if
        # switched, and will be cleaner.
        text = csv.reader(f, delimiter=',', quotechar='"')
        for line in text:
            if (not ref):
                ref = line
                continue
            L.append({})
            for i, val in enumerate(line):
                L[-1][ref[i]] = val
            L[-1]["dist"] = vincenty.vincenty(
                (
                    float(L[-1]["GTFS Latitude"]),
                    float(L[-1]["GTFS Longitude"])
                ),
                (float(lat), float(lon))
            )

    ref.append("dist")
    L = sorted(L, key=lambda item: item["dist"])
    return L


# Returns dictionary of station information. Currently not used.
def station_info():
    L = []
    d = {}
    ref = False
    with open("stations.csv") as f:
        # DictReader instead?
        text = csv.reader(f, delimiter=',', quotechar='"')
        for line in text:
            if (not ref):
                ref = {key: i for i, key in enumerate(line)}
                ref_list = line
                continue
            d[line[ref['GTFS Stop ID']]] = {
                ref_list[i]: val for i, val in enumerate(line)
            }
        return d


# Returns list of "ada accessible" stations. That's quoted because there are a
# lot of specifics in the file. The function assumes that any station that has
# any form of ada accessible anything is entirely ada accessible.
def ada_list(L):
    with open("access.xml") as f:
        aL = xmltodict.parse(f.read())["NYCEquipments"]["equipment"]
    d = collections.defaultdict(lambda: False)
    for station in aL:
        if not d[station["station"]]:
            d[station["station"]] = (station["ADA"] == "Y")
    L = [item for item in L if d[item['Stop Name']]]
    return L


# Adds real time to 'metro' forms of transit, more specifically subway.
def add_real_time(trip):
    lines = set()
    stations = set()
    trips = trip["trips"]
    for obj in trips:
        for obj2 in obj["legs"]:
            if obj2["mode"] == "metro":
                # To avoid making extra network requests, just get the lines
                # and stations needed.
                lines.add(obj2["transit_route"])
                stations.add(obj2["station_start"]["id"])
    # Get the real_time dictionary, in the format dict[line][station].
    real_time = find_station(stations, lines)
    for obj in trips:
        for obj2 in obj["legs"]:
            if obj2["mode"] == "metro":
                obj2["real_time"] = real_time[
                    obj2["transit_route"]][obj2["station_start"]["id"]]
                start_time = dateutil.parser.parse(
                    obj2["statistics"]["start_time"]
                ).replace(tzinfo=None)
                time_now = datetime.now()
                # Filter the real time list so that each arrival/departure time
                # appears only once, and is no earlier than the time of user's
                # estimated arrival at the station. Change the real time into
                # the minutes from now. Sort the new list.
                obj2["real_time"] = sorted(list({
                    int(
                        relativedelta.relativedelta(
                            datetime.fromtimestamp(train_time), time_now
                        ).minutes
                    )
                    # Something here wasn't working, so forgive the messiness.
                    for train_time in obj2["real_time"] if (
                        int(relativedelta.relativedelta(
                            datetime.fromtimestamp(train_time), time_now
                        ).minutes) >= int(relativedelta.relativedelta(
                            start_time, time_now
                        ).minutes)
                    )
                }))
                print(obj2["real_time"][0], time_now, start_time)


# Given an iterable of stations and of trains return the real time dictionary
# of the format dict[line][station].
def find_station(station_ids, trains):
    feed = gtfs_realtime_pb2.FeedMessage()
    with open("secret.json") as f:
        key = json.load(f)["mta"]
    final_times = {}
    # Get a set of the appropriate MTA feed_id. This saves a ton of time in
    # terms of network requests.
    feeds = {FEED_ID[line] for line in trains}
    for feed_id in feeds:
        response = requests.get(
            f"http://datamine.mta.info/mta_esi.php?key={key}&feed_id={feed_id}"
        )
        feed.ParseFromString(response.content)
        # Turn feed into a regular dictionary.
        d = protobuf_to_dict(feed)
        times = collections.defaultdict(
            lambda: collections.defaultdict(lambda: [])
        )
        for i, val in enumerate(d["entity"]):
            if "trip_update" in val:
                for item in val["trip_update"]["stop_time_update"]:
                    # Only looking for specific stations.
                    if (item["stop_id"] in station_ids):
                        if ("arrival" in item):
                            times[
                                val["trip_update"]["trip"]["route_id"]
                            ][item["stop_id"]].append(item["arrival"]["time"])
                        if ("departure" in item):
                            times[
                                val["trip_update"]["trip"]["route_id"]
                            ][item["stop_id"]].append(
                                item["departure"]["time"]
                            )
        # The times dictionary might be edited again, so update the final_times
        # dictionary now.
        final_times.update(times)
    return final_times


if __name__ == "__main__":

    # print(find_station("228N"))
    # feed = gtfs_realtime_pb2.FeedMessage()
    # key = "daf4f75e9255dbfc56da77daf8ffb422"
    # response = requests.get(
    #    f"http://datamine.mta.info/mta_esi.php?key={key}&feed_id=1")
    # feed.ParseFromString(response.content)
    # d = protobuf_to_dict(feed)
    # s = set()
    vehicles = []
    print(station_info())
    # for i,val in enumerate(d["entity"]):
    #     # print(val.keys())
    #     if "vehicle" in val:
    #         vehicles.append(val["vehicle"])
    #     if "alert" in val:
    #         print(val["alert"])
    #     if "trip_update" in val:
    #         s.add(val["trip_update"]["trip"]["route_id"])
    # print(s)
    # print(vehicles[0])
    # print(d["entity"][1]["vehicle"].keys())
    # x = feed.entity[0]
    # print(x)
    # print(len(feed.entity))
    # print(
    #    time.time(), x.trip_update.stop_time_update[0].departure.time,
    #    x.trip_update.trip.route_id)
    # print(x.HasField("trip_update"))
    # print(feed.entity)
    # addr1 = "50, pine street, new york, ny"
    # addr2 = "44, wall street, new york, ny"
    # print(getDirections(
    #    "1449,east 64th street, brooklyn","44, wall street, new york, ny"))
    # lat,lon = get_location_coordinates(addr1)
    # lat2,lon2 = get_location_coordinates(addr2)
    # print(lat, lon)
    # # print(lat2,lon2)
    #
    # # print("done")
    # # # print(is_bike_near(lat,lon,.8))
    # # L=nearest_subway(lat, lon)
    # # print(L)
    # # print(is_subway_near(L,.8))
    # # with open("access.xml") as f:
    # #     x = xmltodict.parse(f.read())
    # x = get_coord_directions(lat2, lon2, lat, lon, False)
    # remove_geometry(x)
    # print(json.dumps(x, indent = 4))
