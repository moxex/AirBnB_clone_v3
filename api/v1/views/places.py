#!/usr/bin/python3
'''Contains the places view for the API.'''
from flask import abort, jsonify, make_response, request
import requests
from api.v1.views import app_views
from api.v1.views.amenities import amenities
from api.v1.views.places_amenities import place_amenities
from models import storage, storage_t
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
    data = request.get_json()
    if type(data) is not dict:
        raise BadRequest(description='Not a JSON')
    all_places = storage.all(Place).values()
    places = []
    places_id = []
    keys_status = (
        all([
            'states' in data and type(data['states']) is list,
            'states' in data and len(data['states'])
        ]),
        all([
            'cities' in data and type(data['cities']) is list,
            'cities' in data and len(data['cities'])
        ]),
        all([
            'amenities' in data and type(data['amenities']) is list,
            'amenities' in data and len(data['amenities'])
        ])
    )
    if keys_status[0]:
        for state_id in data['states']:
            if not state_id:
                continue
            state = storage.get(State, state_id)
            if not state:
                continue
            for city in state.cities:
                new_places = []
                if storage_t == 'db':
                    new_places = list(
                        filter(lambda x: x.id not in places_id, city.places)
                    )
                else:
                    new_places = []
                    for place in all_places:
                        if place.id in places_id:
                            continue
                        if place.city_id == city.id:
                            new_places.append(place)
                places.extend(new_places)
                places_id.extend(list(map(lambda x: x.id, new_places)))
    if keys_status[1]:
        for city_id in data['cities']:
            if not city_id:
                continue
            city = storage.get(City, city_id)
            if city:
                new_places = []
                if storage_t == 'db':
                    new_places = list(
                        filter(lambda x: x.id not in places_id, city.places)
                    )
                else:
                    new_places = []
                    for place in all_places:
                        if place.id in places_id:
                            continue
                        if place.city_id == city.id:
                            new_places.append(place)
                places.extend(new_places)
    del places_id
    if all([not keys_status[0], not keys_status[1]]) or not data:
        places = all_places
    if keys_status[2]:
        amenity_ids = []
        for amenity_id in data['amenities']:
            if not amenity_id:
                continue
            amenity = storage.get(Amenity, amenity_id)
            if amenity and amenity.id not in amenity_ids:
                amenity_ids.append(amenity.id)
        del_indices = []
        for place in places:
            place_amenities_ids = list(map(lambda x: x.id, place.amenities))
            if not amenity_ids:
                continue
            for amenity_id in amenity_ids:
                if amenity_id not in place_amenities_ids:
                    del_indices.append(place.id)
                    break
        places = list(filter(lambda x: x.id not in del_indices, places))
    result = []
    for place in places:
        obj = place.to_dict()
        if 'amenities' in obj:
            del obj['amenities']
        result.append(obj)
    return jsonify(result)
