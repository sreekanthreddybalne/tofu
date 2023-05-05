from __future__ import absolute_import, unicode_literals
import smtplib
import http.client
import urllib # Python URL functions
import urllib.request, urllib.error, urllib.parse
AUTH_KEY = "314918A5Dv9p4tMQQ5e2b557fP1"
def sendSMS(mobileNo, message):
	mobiles=mobileNo
	message=message
	sender="TOFUIN"
	route="4"
	values={
		'authkey':AUTH_KEY,
		'mobiles':mobiles,
		'message':message,
		'sender':sender,
		'route':route
	}
	url = "http://api.msg91.com/api/sendhttp.php" # API URL
	postdata = urllib.parse.urlencode(values).encode("utf-8") # URL encoding the data here.
	req = urllib.request.Request(url, postdata) #synchronous request
	response = urllib.request.urlopen(req) #infinitely waiting for response
	output = response.read() #Read response status codes
	return output
