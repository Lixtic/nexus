"""
These are all the tools used in the NexusRaven V2 demo! You can provide any tools you want to Raven.

Nothing in this file is specific to Raven, code/information related to Raven can be found in the `raven_demo.py` file.

For more information about the Google Maps Places API Python client, see https://github.com/googlemaps/google-maps-services-python
"""
from typing import Dict, List

from math import radians, cos, sin, asin, sqrt

import random

import requests

from googlemaps import Client

from config import DemoConfig


class Tools:
    def __init__(self, config: DemoConfig) -> None:
        self.config = config

        self.gmaps = Client(config.gmaps_client_key)
        self.client_ip: str | None = None

    def haversine(self, lon1, lat1, lon2, lat2) -> float:
        """
        Calculate the great circle distance in kilometers between two points on the earth (specified in decimal degrees).
        """
        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of Earth in kilometers. Use 3956 for miles
        return round(c * r, 2)

    def get_current_location(self) -> str:
        """
        Returns the current location. ONLY use this if the user has not provided an explicit location in the query.
        """
        try:
            response = requests.get(f"http://ip-api.com/json/{self.client_ip}")
            location_data = response.json()
            city = location_data["city"]
            region = location_data["regionName"]
            country = location_data["countryCode"]
            return f"{city}, {region}, {country}"
        except:
            return "San Francisco, California, US"

    def sort_results(
        self, places: list, sort: str, descending: bool = True, first_n: int = None
    ) -> List:
        """
        Sorts the results by either 'distance', 'rating' or 'price'.

        - places (list): The output list from the recommendations.
        - sort (str): If set, sorts by either 'distance' or 'rating' or 'price'. ONLY supports 'distance' or 'rating' or 'price'.
        - descending (bool): If descending is set, setting this boolean to true will sort the results such that the highest values are first.
        - first_n (int): If provided, only retains the first n items in the final sorted list.

        When people ask for 'closest' or 'nearest', sort by 'distance'.
        When people ask for 'cheapest' or 'most expensive', sort by 'price'.
        When people ask for 'best' or 'highest rated', sort by rating.
        """

        if not sort:
            return places

        if sort == "price":
            sort = "price_level"

        items = sorted(
            places,
            key=lambda x: x.get(sort, float("inf")),
            reverse=descending,
        )

        if first_n:
            items = items[:first_n]
        return items

    def get_latitude_longitude(self, location: str) -> List:
        """
        Given a city name, this function provides the latitude and longitude of the specific location.

        - location: This can be a city like 'Austin', or a place like 'Austin Airport', etc.
        """
        if (
            isinstance(location, list)
            and len(location) != 0
            and isinstance(location[0], dict)
        ):
            return location

        # For response content, see https://developers.google.com/maps/documentation/places/web-service/search-find-place#find-place-responses
        results = self.gmaps.find_place(
            location, input_type="textquery", location_bias="ipbias"
        )
        if results["status"] != "OK":
            return []

        # We always use the first candidate
        place_id = results["candidates"][0]["place_id"]

        # For response format, see https://developers.google.com/maps/documentation/places/web-service/details#PlaceDetailsResponses
        place_details = self.gmaps.place(place_id=place_id)["result"]
        return [place_details]

    def get_distance(self, place_1: str, place_2: str):
        """
        Provides distance between two locations. Do NOT provide latitude longitude, but rather, provide the string descriptions.

        Allows you to provide output from the get_recommendations API.

        - place_1: The first location.
        - place_2: The second location.
        """
        if isinstance(place_1, list) and len(place_1) > 0:
            place_1 = place_1[0]
        if isinstance(place_2, list) and len(place_2) > 0:
            place_2 = place_2[0]

        if isinstance(place_1, dict):
            place_1: str = place_1["name"]
        if isinstance(place_2, dict):
            place_2: str = place_2["name"]

        latlong_1 = self.get_latitude_longitude(place_1)
        if len(latlong_1) == 0:
            return f"No place found for `{place_1}`. Please be more explicit."

        latlong_2 = self.get_latitude_longitude(place_2)
        if len(latlong_2) == 0:
            return f"No place found for `{place_2}`. Please be more explicit."

        latlong_1 = latlong_1[0]
        latlong_2 = latlong_2[0]

        latlong_values_1 = latlong_1["geometry"]["location"]
        latlong_values_2 = latlong_2["geometry"]["location"]

        dist = self.haversine(
            latlong_values_1["lng"],
            latlong_values_1["lat"],
            latlong_values_2["lng"],
            latlong_values_2["lat"],
        )
        dist = dist * 0.621371

        return [
            latlong_1,
            latlong_2,
            f"The distance between {place_1} and {place_2} is {dist:.3f} miles",
        ]

    def get_recommendations(self, topics: list, lat_long: tuple):
        """
        Returns the recommendations for a specific topic that is of interest. Remember, a topic IS NOT an establishment. For establishments, please use another function.

        - topics (list): A list of topics of interest to pull recommendations for. Can be multiple words.
        - lat_long (tuple): The lat_long of interest.
        """
        if len(lat_long) == 0:
            return []

        topic = " ".join(topics)
        latlong = lat_long[0]["geometry"]["location"]
        # For response format, see https://developers.google.com/maps/documentation/places/web-service/search-find-place#find-place-responses
        results = self.gmaps.places(
            query=topic,
            location=latlong,
        )
        return results["results"]

    def find_places_near_location(
        self, type_of_place: list, location: str, radius_miles: int = 50
    ) -> List[Dict]:
        """
        Find places close to a very defined location.

        - type_of_place (list): The type of place. This can be something like 'restaurant' or 'airport'. Make sure that it is a physical location. You can provide multiple words.
        - location (str): The location for the search. This can be a city's name, region, or anything that specifies the location.
        - radius_miles (int): Optional. The max distance from the described location to limit the search. Distance is specified in miles.
        """
        place_details = self.get_latitude_longitude(location)
        if len(place_details) == 0:
            return []
        place_details = place_details[0]
        location = place_details["name"]
        latlong = place_details["geometry"]["location"]

        type_of_place = " ".join(type_of_place)
        # Perform the search using Google Places API
        # For response format, see https://developers.google.com/maps/documentation/places/web-service/search-nearby#nearby-search-responses
        places_nearby = self.gmaps.places_nearby(
            location=(latlong["lat"], latlong["lng"]),
            keyword=type_of_place,
            radius=radius_miles * 1609.34,
        )
        if places_nearby["status"] != "OK":
            return []

        places_nearby = places_nearby["results"]
        places = []
        for place_nearby in places_nearby:
            place_location = place_nearby["geometry"]["location"]
            distance = self.haversine(
                latlong["lng"],
                latlong["lat"],
                place_location["lng"],
                place_location["lat"],
            )
            if distance == 0.0:
                continue

            distance = distance * 0.621371
            place_nearby["distance"] = f"{distance} miles from {location}"
            places.append(place_nearby)

        if len(places) == 0:
            return []

        return self.sort_results(places, sort="distance", descending=False)

    def get_some_reviews(self, place_names: list, location: str = None):
        """
        Given an establishment (or place) name, return reviews about the establishment.

        - place_names (list): The name of the establishment. This should be a physical location name. You can provide multiple inputs.
        - location (str) : The location where the restaurant is located. Optional argument.
        """
        all_reviews = []
        for place_name in place_names:
            if isinstance(place_name, str):
                if location and isinstance(location, list) and len(location) > 0:
                    # Sometimes location will be a list of relevant places from the API.
                    # We just use the first one.
                    location = location[0]
                elif location and isinstance(location, list):
                    # No matching spaces found in the API, len of 0
                    location = None
                if location and isinstance(location, dict):
                    # Weird response from the API, likely a timeout error, disable geoloc
                    location = None
                if location and isinstance(location, str):
                    place_name += " , " + location
            elif (
                isinstance(place_name, dict)
                and "results" in place_name
                and "name" in place_name["results"]
            ):
                place_name = place_name["results"]["name"]
            elif isinstance(place_name, dict) and "name" in place_name:
                place_name = place_name["name"]

            place_details = self.get_latitude_longitude(place_name)
            if len(place_details) == 0:
                continue
            place_details = place_details[0]

            reviews = place_details.get("reviews", [])

            for review in reviews:
                review["for_location"] = place_name
                review["formatted_address"] = place_details["formatted_address"]

            all_reviews.extend(reviews)

        random.shuffle(all_reviews)

        return all_reviews
