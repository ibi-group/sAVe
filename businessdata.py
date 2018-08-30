import sqlite3
import csv
import random
import api


# Creates business table schema. For use everywhere. Takes a cursor/connection.
def create_business_table(cursor):
    query = '''CREATE TABLE IF NOT EXISTS businesses(
                    name TEXT DEFAULT NULL,
                    password TEXT DEFAULT NULL,
                    category TEXT DEFAULT NULL,
                    address TEXT DEFAULT NULL,
                    latitude TEXT DEFAULT NULL,
                    longitude TEXT DEFAULT NULL,
                    display_on_map INTEGER DEFAULT 0,
                    promotion INTEGER DEFAULT 0,
                    discount INTEGER DEFAULT 0,
                    id INTEGER PRIMARY KEY AUTOINCREMENT)
            '''
    cursor.execute(query)


# Get businesses that choose to display themselves on the map.
def get_displayed_locations():
    connection = sqlite3.connect('business.db')
    connection.row_factory = sqlite3.Row
    with connection:
        create_business_table(connection)
        locations = connection.execute(
            '''SELECT latitude, longitude,
                        name, address, promotion, discount
                        FROM businesses WHERE
                display_on_map = 1
            '''
        ).fetchall()
    return locations


# Given business name (username), and password, check that they match.
def verify_business(name, password):
    connection = sqlite3.connect('business.db')
    with connection:
        create_business_table(connection)
        password_check = connection.execute(
            '''
            SELECT password FROM businesses WHERE name = ?
            ''', (name,)
        ).fetchone()
    if (not password_check):
        return False
    return (password_check[0] == password)


# Add business given business name and password.
def add_business(name, password):
    connection = sqlite3.connect('business.db')
    with connection:
        create_business_table(connection)
        if (
            connection.execute(
                '''
                SELECT * FROM businesses WHERE name = ?
                ''', (name,)
            ).fetchone()
        ):
            return False
        connection.execute(
            '''
            INSERT INTO businesses (name, password) VALUES (?,?)
            ''', (name, password,)
        )
    return True


# Get business id (user id) given business name (username).
def get_business_id(name):
    connection = sqlite3.connect('business.db')
    with connection:
        create_business_table(connection)
        return connection.execute(
            '''
            SELECT id FROM businesses WHERE name = ?
            ''', (name,)
        ).fetchone()


# Get business settings/preferences given id.
def get_setting(user_id):
    connection = sqlite3.connect('business.db')
    connection.row_factory = sqlite3.Row
    with connection:
        settings = connection.execute(
            '''
            SELECT
                category, address,
                display_on_map, promotion,
                discount
                FROM businesses
                WHERE id = ?''',
            (user_id,)).fetchone()
    return settings


# Save business preferences given preferences and id.
def save_settings(user_id, settings):
    # Combine into a single dictionary for ease.
    business_dict = {**dict(user_id=user_id), **settings}
    print(business_dict)
    connection = sqlite3.connect('business.db')
    with connection:
        if settings["address"]:
            business_dict["latitude"], business_dict["longitude"] = \
                api.get_location_coordinates(settings["address"])
        connection.execute('''UPDATE businesses SET
                                category = :category,
                                address = :address,
                                latitude = :latitude,
                                longitude = :longitude,
                                display_on_map = :display_on_map,
                                promotion = :promotion,
                                discount = :discount
                                WHERE
                                    id = :user_id''', business_dict)
    return True


# Get all business locations for display on statistics page.
def get_all_locations():
    connection = sqlite3.connect('business.db')
    connection.row_factory = sqlite3.Row
    with connection:
        create_business_table(connection)
        locations = connection.execute(
            '''SELECT latitude, longitude,
                        name, address
                        FROM businesses
            '''
        ).fetchall()
    return locations


# Get all categories, for statistics filtering.
def get_categories():
    connection = sqlite3.connect('business.db')
    connection.row_factory = sqlite3.Row
    with connection:
        create_business_table(connection)
        categories = connection.execute(
            '''SELECT DISTINCT category FROM businesses'''
        ).fetchall()
    return categories


# Get data totals for statistics.
def get_data():
    connection = sqlite3.connect('business.db')
    connection.row_factory = sqlite3.Row
    with connection:
        create_business_table(connection)
        count_fetch = connection.execute(
            '''
            SELECT
                COUNT(NULLIF(display_on_map,0)) as displayed,
                COUNT(NULLIF(promotion,0)) as promotion,
                COUNT(NULLIF(discount,0)) as discounted,
                COUNT(DISTINCT category) as categories,
                COUNT(name) as registered
            FROM businesses
            ''').fetchone()
        # If it's empty, return False. This may not be handled on other end.
        if (not count_fetch):
            return False
    return count_fetch


# Get data filtered by category and other filters, as designated on
# business data page.
def get_filtered_data(filters, type_, categories):
    connection = sqlite3.connect('business.db')
    connection.row_factory = sqlite3.Row
    with connection:
        create_business_table(connection)
        # Will query like "WHERE filters[0] = 1 type_ filters[1] = 1".
        # type_ will be AND or OR. categories_string will be inserted.
        reference = {
            "displayed": "display_on_map",
            "promotion": "promotion",
            "discounted": "discount"
        }
        filters = [reference[key] for key in filters]
        filter_string = (" = 1 " + type_ + " ").join(filters)
        categories_string = ", ".join(categories)
        query = '''SELECT
                        COUNT(NULLIF(display_on_map,0)) as displayed,
                        COUNT(NULLIF(promotion,0)) as promotion,
                        COUNT(discount) as discounted,
                        COUNT(DISTINCT category) as categories,
                        COUNT(name) as registered
                    FROM businesses
                    WHERE ({} = 1) {} (category IN (?))
                '''
        query = query.format(filter_string, type_)
        count_fetch = connection.execute(query, (categories_string,)
                                         ).fetchone()
        count_dict = {}
        if (not count_fetch):
            return False
        return count_fetch


def get_filtered_locations(filters, type_, categories):
    connection = sqlite3.connect('business.db')
    connection.row_factory = sqlite3.Row
    with connection:
        create_business_table(connection)
        # The names as they're displayed do not match the database keys.
        # This fixes it, sort of.
        reference = {
            "displayed": "display_on_map",
            "promotion": "promotion",
            "discounted": "discount"
        }
        filters = [reference[key] for key in filters]
        # Will query like "WHERE filters[0] = 1 type_ filters[1] = 1".
        # type_ will be AND or OR.
        filter_string = (" = 1 " + type_ + " ").join(filters)
        categories_string = ", ".join(categories)
        query = '''SELECT
                        latitude, longitude,
                        name, address
                    FROM businesses
                    WHERE ({} = 1) {} (category IN (?))
                '''
        query = query.format(filter_string, type_)
        count_fetch = connection.execute(query, (categories_string,)
                                         ).fetchall()
        count_dict = {}
        if (not count_fetch):
            return {}
        return count_fetch


if __name__ == "__main__":
    pass
    # connection = sqlite3.connect('business.db')
    # with connection, open('businesses.csv') as csvfile:
    #     reader = csv.DictReader(csvfile)
    #     create_business_table(connection)
    #     for i, row in enumerate(reader):
    #         if (i > 100):
    #             break
    #         input_values = dict(row)
    #         input_values["display_on_map"] = random.randint(0, 1)
    #         connection.execute('''
    #             INSERT INTO businesses
    #                 (
    #                     name, address, latitude, longitude, display_on_map
    #                 )
    #             VALUES
    #                 (
    #                     :name, :address, :latitude, :longitude,
    #                        :display_on_map
    #                 )
    #             ''',
    #                            input_values)
    #     connection.execute('''
    #         INSERT INTO businesses
    #             (
    #                 name, address, latitude, longitude, display_on_map,
    #                category
    #             )
    #         VALUES
    #             (
    #             "IBI","44 wall street, new york, ny",
    #             "40.706584", "-74.009611", 1, "office"
    #             )
    #         '''
    #     )
