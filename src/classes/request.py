import urllib, urllib2, json
from xml.dom.minidom import parseString
import utils


class Request:
    @staticmethod
    def getXml(url, body={}, headers={}):
        utils.log("Requesting %s..." % url)

        try:
            request = urllib2.Request(url, urllib.urlencode(body), headers)
            response = urllib2.urlopen(request)
            content = response.read()
        except:
            return None

        return parseString(str(content))

    @staticmethod
    def getJson(url, headers={}):
        utils.log("Requesting %s..." % url)

        try:
            request = urllib2.Request(url, None, headers)
            response = str(urllib2.urlopen(request).read())
            # Read JSONP too
            return json.loads(response[response.find("{"):])
        except:
            return None

    @staticmethod
    def get(url, headers={}):
        utils.log("Requesting %s..." % url)

        try:
            request = urllib2.Request(url, None, headers)
            response = str(urllib2.urlopen(request).read())
            return response
        except:
            return None
