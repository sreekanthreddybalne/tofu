import requests, json
import googlemaps
from datetime import datetime

API_KEY = "AIzaSyC7gbhCXFvCOIp3IAs3Kaco7WRZg-Jtn94"
gmaps = googlemaps.Client(key='AIzaSyC7gbhCXFvCOIp3IAs3Kaco7WRZg-Jtn94')
res = gmaps.distance_matrix(origins="place_id:ChIJLbZ-NFv9DDkRQJY4FbcFcgM", destinations="place_id:ChIJm8RPaUr9DDkRDBt4YsluSqI")
print(res)
