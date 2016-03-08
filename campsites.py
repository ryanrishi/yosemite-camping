#!/usr/bin/env python
import argparse
import copy
import requests
import ConfigParser
from twilio.rest import TwilioRestClient

from urlparse import parse_qs
from datetime import datetime
from bs4 import BeautifulSoup

# Hardcoded list of campgrounds I'm willing to sleep at
PARKS = {
    '70925': 'UPPER PINES',
    '70928': 'LOWER PINES',
    '70927': 'NORTH PINES',
    '73635': 'STANISLAUS',
    '70926': 'TUOLOMNE MEADOWS'
}

# Sets the search location to yosemite
LOCATION_PAYLOAD = {
    'currentMaximumWindow': '12',
    'locationCriteria': 'yosemite',
    'interest': '',
    'locationPosition': '',
    'selectedLocationCriteria': '',
    'resetAllFilters':    'false',
    'filtersFormSubmitted': 'false',
    'glocIndex':    '0',
    'googleLocations':  'Yosemite National Park, Yosemite Village, CA 95389, USA|-119.53832940000001|37.8651011||LOCALITY'
}

# Sets the search type to camping
CAMPING_PAYLOAD = {
    'resetAllFilters':  'false',
    'filtersFormSubmitted': 'true',
    'sortBy':   'RELEVANCE',
    'category': 'camping',
    'selectedState':    '',
    'selectedActivity': '',
    'selectedAgency':   '',
    'interest': 'camping',
    'usingCampingForm': 'true'
}

# Runs the actual search
PAYLOAD = {
    'resetAllFilters':   'false',
    'filtersFormSubmitted': 'true',
    'sortBy':   'RELEVANCE',
    'category': 'camping',
    'availability': 'all',
    'interest': 'camping',
    'usingCampingForm': 'false'
}


BASE_URL = "http://www.recreation.gov"
UNIF_SEARCH = "/unifSearch.do"
UNIF_RESULTS = "/unifSearchResults.do"

def findCampSites(args):
    payload = generatePayload(args['start_date'], args['end_date'])

    content_raw = sendRequest(payload)
    html = BeautifulSoup(content_raw)
    sites = getSiteList(html)
    return sites

def formatDate(date):
    date_object = datetime.strptime(date, "%Y-%m-%d")
    date_formatted = datetime.strftime(date_object, "%a %b %d %Y")
    return date_formatted

def generatePayload(start, end):
    payload = copy.copy(PAYLOAD)
    payload['arrivalDate'] = formatDate(start)
    payload['departureDate'] = formatDate(end)
    return payload

def getSiteList(html):
    sites = html.findAll('div', {"class": "check_avail_panel"})
    results = []
    for site in sites:
        if site.find('a', {'class': 'book_now'}):
            get_url = site.find('a', {'class': 'book_now'})['href']
            # Strip down to get query parameters
            get_query = get_url[get_url.find("?") + 1:] if get_url.find("?") >= 0 else get_url
            if get_query:
                get_params = parse_qs(get_query)
                siteId = get_params['parkId']
                if siteId and siteId[0] in PARKS:
                    results.append("%s, Booking Url: %s" % (PARKS[siteId[0]], BASE_URL + get_url))
    return results

def sendRequest(payload):
    with requests.Session() as s:

        s.get(BASE_URL + UNIF_RESULTS) # Sets session cookie
        s.post(BASE_URL + UNIF_SEARCH, LOCATION_PAYLOAD) # Sets location to yosemite
        s.post(BASE_URL + UNIF_SEARCH, CAMPING_PAYLOAD) # Sets search type to camping

        resp = s.post(BASE_URL + UNIF_SEARCH, payload) # Runs search on specified dates
        if (resp.status_code != 200):
            raise Exception("failedRequest","ERROR, %d code received from %s".format(resp.status_code, BASE_URL + SEARCH_PATH))
        else:
            return resp.text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", type=str, help="Start date [YYYY-MM-DD]")
    parser.add_argument("--end_date", type=str, help="End date [YYYY-MM-DD]")

    # Set up Twilio
    config_parser = ConfigParser.ConfigParser()
    config_parser.readfp(open(r'config'))
    twilio_sid = config_parser.get('twilio', 'ACCOUNT_SID')
    twilio_token = config_parser.get('twilio', 'AUTH_TOKEN')
    twilio_from = config_parser.get('twilio', 'from_')
    twilio_to = config_parser.get('twilio', 'to')

    twilio_client = TwilioRestClient(twilio_sid, twilio_token)

    args = parser.parse_args()
    sites = findCampSites(vars(args))
    if sites:
        for site in sites:
            print site
            twilio_client.messages.create(to=twilio_to, from_=twilio_from, body=site)
