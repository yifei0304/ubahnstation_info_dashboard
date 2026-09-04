#!/usr/bin/python3
import bottle
import json
import urllib.request
import urllib.parse
import os


@bottle.route('/route', method=['GET'])
def route():
    try:
        origin_lat = bottle.request.params.get('olat')
        origin_lng = bottle.request.params.get('olng')
        dest_lat   = bottle.request.params.get('dlat')
        dest_lng   = bottle.request.params.get('dlng')

        if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
            return bottle.HTTPResponse(
                json.dumps({'status': 'error', 'message': 'Missing coordinates'}),
                status=400,
                headers={'content-type': 'application/json', 'Access-Control-Allow-Origin': '*'}
            )

        url = 'https://routes.googleapis.com/directions/v2:computeRoutes'
        body = json.dumps({
            'origin':      {'location': {'latLng': {'latitude': float(origin_lat), 'longitude': float(origin_lng)}}},
            'destination': {'location': {'latLng': {'latitude': float(dest_lat),   'longitude': float(dest_lng)}}},
            'travelMode': 'WALK'
        }).encode()

        req = urllib.request.Request(url, data=body, method='POST', headers={
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': 'AIzaSyCr1iEGScMOIg1OiMr49FoFvWw12pYalUw',
            'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        route_data = data.get('routes', [{}])[0]
        return bottle.HTTPResponse(
            json.dumps({'status': 'ok',
                        'duration': route_data.get('duration', '0s'),
                        'distanceMeters': route_data.get('distanceMeters', 0)}),
            status=200,
            headers={'content-type': 'application/json', 'Access-Control-Allow-Origin': '*'}
        )
    except Exception as e:
        return bottle.HTTPResponse(
            json.dumps({'status': 'error', 'message': str(e)}),
            status=500,
            headers={'content-type': 'application/json', 'Access-Control-Allow-Origin': '*'}
        )


bottle.run(host='::0', port=8081)
