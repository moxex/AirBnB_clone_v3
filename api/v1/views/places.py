#!/usr/bin/python3
'''Contains the places view for the API.'''
from flask import abort, jsonify, make_response, request
import requests
from api.v1.views import app_views
from api.v1.views.amenities import amenities
from api.v1.views.places_amenities import place_amenities
from models import storage
from models.amenity import Amenity
from models.city import City
from models.place import Place
from models.state import State
from models.user import User
import json
from os import getenv


@app_views.route('cities/<city_id>/places',
                 methods=['GET'], strict_slashes=False)
def place(city_id):
    """Retrieves the list of all Place objects of a City"""
    obj_city = storage.get(City, city_id)
    if not obj_city:
        abort(404)

    return jsonify([obj.to_dict() for obj in obj_city.places])


@app_views.route('/places/<place_id>', methods=['GET'], strict_slashes=False)
def single_place(place_id):
    """Retrieves a Place object"""
    obj = storage.get(Place, place_id)
    if not obj:
        abort(404)
    return jsonify(obj.to_dict())


@app_views.route('/places/<place_id>',
                 methods=['DELETE'], strict_slashes=False)
def del_place(place_id):
    """Returns an empty dictionary with the status code 200"""
    obj = storage.get(Place, place_id)
    if not obj:
        abort(404)
    obj.delete()
    storage.save()
    return make_response(jsonify({}), 200)


@app_views.route('cities/<city_id>/places',
                 methods=['POST'], strict_slashes=False)
def post_place(city_id):
    """Returns the new Place with the status code 201"""
    obj_city = storage.get(City, city_id)
    if not obj_city:
        abort(404)

    new_place = request.get_json()
    if not new_place:
        abort(400, 'Not a JSON')
    if 'user_id' not in new_place:
        abort(400, "Missing user_id")
    user_id = new_place['user_id']
    obj_user = storage.get(User, user_id)
    if not obj_user:
        abort(404)
    if 'name' not in new_place:
        abort(400, "Missing name")

    obj = Place(**new_place)
    setattr(obj, 'city_id', city_id)
    storage.new(obj)
    storage.save()
    return make_response(jsonify(obj.to_dict()), 201)


@app_views.route('/places/<place_id>', methods=['PUT'], strict_slashes=False)
def put_place(place_id):
    """Returns the Place object with the status code 200"""
    obj = storage.get(Place, place_id)
    if not obj:
        abort(404)

    req = request.get_json()
    if not req:
        abort(400, "Not a JSON")

    for k, v in req.items():
        if k not in ['id', 'user_id', 'city_id', 'created_at', 'updated_at']:
            setattr(obj, k, v)

    storage.save()
    return make_response(jsonify(obj.to_dict()), 200)


@app_views.route('/places_search', methods=['POST'], strict_slashes=False)
def places_search():
    """
    retrieves all Place objects depending
    of the JSON in the body of the request
    """
    places_list = []
    place_dicts = []
    cities_list = []
    removal_list = []
    empty = True
    content = request.get_json(silent=True)

    if type(content) is dict:
        for key, value in content.items():
            if len(content[key]) > 0:
                empty = False

        if len(content) == 0 or empty is True:
            places = storage.all(Place).values()
            for place in places:
                place_dicts.append(place.to_dict())

        if "states" in content:
            for state in content["states"]:
                state_obj = storage.get(State, state)
                if state_obj:
                    for city in state_obj.cities:
                        cities_list.append(city)

        if "cities" in content:
            for city in content["cities"]:
                city_obj = storage.get(City, city)
                if city_obj:
                    cities_list.append(city_obj)

        for city in cities_list:
            for place in city.places:
                places_list.append(place)

        if "amenities" in content:
            for place in places_list:
                for amenity in content["amenities"]:
                    amenity_obj = storage.get(Amenity, amenity)
                    if amenity_obj:
                        if amenity_obj not in place.amenities:
                            removal_list.append(place)
                            break

        for place in removal_list:
            if place in places_list:
                places_list.remove(place)

        for place in places_list:
            place_dicts.append(place.to_dict())

        return jsonify(place_dicts)

    else:
        return make_response(jsonify("Not a JSON"), 400)
