#!/usr/bin/python
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# This is a python scipt that we use to count members of the IEEE's
# Special Technical Community on Sustainable Computing (STC-SC).
# To join STC-SC, please visit: http://stc-sustainable-computing.ieee.net/
#
# The script creates a csv file with member names and contact
# information by merging data from three sources:
#     1. A Facebook group located at: http://www.facebook.com/groups/STC.Sustainable.Computing/members/
#     2. A LinkedIn group located at: http://www.linkedin.com/groups?viewMembers=&gid=4092681
#     3. A Google spreadsheet located at: https://docs.google.com/spreadsheet/ccc?key=0AjUwI2hDSR6_dC1KSXFqVldGM1NSWnFLYnppZmY0S0E&pli=1#gid=0
#
# Got a question? Found a bug? Please contact the author directly.
# Please attach this python script, its output, the log file and the
# resulting list to an email and send it to:
# Sergey Blagodurov (mailto: sergey_blagodurov@sfu.ca)
# 
# Version 1.5
# Requires:
# python 3 
# tweepy package for the Twitter support (get it from here: http://tweepy.googlecode.com/files/tweepy-1.4-py3.tar.gz) 
# Usage: 
# export LANG=it_IT.UTF-8
# python member-counting.py
# Instructions:
#     1. Specify your logins in global variables userFB, userLinkedIn,
#     userWeb (see below).
#     2. Specify your source groups and docs in global variables 
#     FBgroupURL, mobileFBgroupID, LinkedInGID, GoogleSpreadsheetKey, TwitterScreenName (see below).
#     3. Launch the script. You'll be prompted for the passwords.
#     4. Wait until the script finishes. You will then find the log
#     file and the resulting csv list in the same directory with
#     the script.
#
# Links:
# many thanks to:
# http://ruel.me/blog/2010/11/26/scrape-your-facebook-friends-contact-info-with-python/
# LinkedIn last-name-as-initial issue (consider signing up for a
# premium account to see full names):
# https://help.linkedin.com/app/answers/detail/a_id/4509

import sys, re, urllib.parse, urllib.request, urllib.error, http.cookiejar, html.parser, getpass
import time
from time import strftime
import logging
import getpass
import csv
import codecs
import tweepy

filename = "members_list"

logger = logging.getLogger('member-counting')

# logins for the sources
userFB = ''
userLinkedIn = ''
userWeb = ''

# do not store the password here! You will be prompted for the password when you launch the script 
passwFB = ''
passwLinkedIn = ''
passwWeb = ''

# URL of the FB group for which to count members:
FBgroupURL = 'http://www.facebook.com/groups/STC.Sustainable.Computing/members/'

# ID of the mobile counterpart of the group.
# Obtain it by signing up to http://m.facebook.com and then looking at the URL of the group at http://m.facebook.com/groups/
mobileFBgroupID = '260557033966377'

# LinkedIn group ID (obtain it by looking at the URL of the group members page on the website):
LinkedInGID = '4092681'

# Google spreadsheet key (its in the doc URL): 
GoogleSpreadsheetKey = '0AjUwI2hDSR6_dC1KSXFqVldGM1NSWnFLYnppZmY0S0E'

# Twitter screen name of the group: 
TwitterScreenName = 'stcsn'

#Timestamp
#Full Name
#LinkedIn Name
#Email
#Why do you want to join IEEE STC-SC?
#Affiliation
#Others
#Group
from collections import defaultdict
contact_info = defaultdict(list)
contact_info_linkedin = defaultdict(list)


class FormScraper(html.parser.HTMLParser):
    """
    Scrapes the Facebook login page for form values that need to be submitted on login.
    Necessary because the form values change each time the login page is loaded.
 
    Usage:
    form_scraper = FormScraper()
    form_scraper.feed(html_from_facebook)
    form_values = form_scraper.values
    """
 
    def __init__(self, *args, **kwargs):
        html.parser.HTMLParser.__init__(self, *args, **kwargs)
        self.in_form = False
        self.values = []
 
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs)
 
        if tag == 'form' and attrs['id'] == 'login_form':
            self.in_form = True
        elif self.in_form and tag == 'input' and attrs['type'] == 'hidden':
            self.values.append( (attrs['name'], attrs['value']) )
 
    def handle_endtag(self, tag):
        if tag.lower() == 'form' and self.in_form:
            self.in_form = False





def mainFB():
    global userFB
    global passwFB
    
    global FBgroupURL
    global mobileFBgroupID
    
    user = userFB
    passw = passwFB

    # Set needed modules
    CHandler = urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    browser = urllib.request.build_opener(CHandler)
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
    urllib.request.install_opener(browser)
 

    #Retrieve login form data and initialize the cookies
    printToLog('Initializing FB parsing...')
    res = browser.open('https://www.facebook.com/login.php')
 
    #Determine string encoding
    content_type = res.info()['Content-Type'].split('; ')
    encoding = 'utf-8'
    if len(content_type) > 1 and content_type[1].startswith('charset'):
        encoding = content_type[1].split('=')[1]
    html = str(res.read(), 'utf-8')
    res.close()
 
    #scrape form for hidden inputs, add email and password to values
    form_scraper = FormScraper()
    form_scraper.feed(html)
    form_data = form_scraper.values
    form_data.extend( [('email', user), ('pass', passw)] )
    #HACK: urlencode doesn't like strings that aren't encoded with the 'encode' function.
    #Using html.encode(encoding) doesn't help either. why ??
    form_data = [ ( x.encode(encoding), y.encode(encoding) ) for x,y in form_data ]
    data = urllib.parse.urlencode(form_data)
 
    # Login
    printToLog('Logging in to FB account ' + user)
    # as taken from the action attribute of the login form:
    res = browser.open('https://login.facebook.com/login.php?login_attempt=1', data.encode('ascii'))
    rcode = res.code
    printToLog(rcode)
#    if not re.search('home\.php$', res.url):
#        print('Login Failed')
#        exit(2)
    res.close()


    printToLog("Getting FB group members info...")

    printToLog("fetching FB group members page: " + FBgroupURL)
    res = browser.open(FBgroupURL)
    parp = res.read()
    m = re.findall('www\.facebook\.com\/([a-zA-Z0-9\w\-\.?=]+)" data-hovercard', parp.decode('utf8'))
    res.close()
    # uniqueness:
    m = list(set(m))
    
    # adding names of the FB group members with inactive FB accounts to the contact list
    inactive_fb_accounts = re.findall('class="fsl fwb fcb"><span>([a-zA-Z0-9\w ]+)<\/span>', parp.decode('utf8'))
    # uniqueness:
    inactive_fb_accounts = list(set(inactive_fb_accounts))
    for full_name in inactive_fb_accounts:
        printToLog("parsing inactive FB profile of " + full_name + "...")
        appendToContact("", full_name, "", "", "", "", "", "FB")
    
    
    # mobile Facebook parsing (we need to use both regular and mobile version
    # regular - for acounting inactive accounts (see above)
    # mobile - to account for more than 96 members (the script currently does not allow to press "See more" ajax button at http://www.facebook.com/groups/STC.Sustainable.Computing/members/)
    # that being said, some members could slip from the script if they are inactive and happened to be displayed after 96th position
    mbase_page0 = "http://m.facebook.com/groups/" + mobileFBgroupID + "?view=members"
    mbase_page = 'http://m.facebook.com/browse/group/members/?id=' + mobileFBgroupID + '&start='
    mm = []
    mpage = 0
    while True:
        if mpage == 0:
            mcur_url = mbase_page0
        else:
            mcur_url = mbase_page + str(mpage)
        printToLog("fetching mobile FB group members page: " + mcur_url)
        mres = browser.open(mcur_url)
        mparp = mres.read()
        mm = mm + re.findall('"\/([a-zA-Z0-9\w\-\.]+)\?fref=pb', mparp.decode('utf8'))
        mm = mm + re.findall('"\/([a-zA-Z0-9\w\-\.?=]+)&amp;fref=pb', mparp.decode('utf8'))
        mres.close()
        if re.search('See More', mparp.decode('utf8')):
            if mpage == 0:
                mpage += 10
            else:
                mpage += 30
        else:
            break
    # uniqueness:
    mm = list(set(mm))
    
    m = m + mm
    # uniqueness:
    m = list(set(m))
    
    len_m = len(m) + len(inactive_fb_accounts)
    printToLog(str(len_m) + " FB profiles found.")
    print(str(len_m) + " FB profiles found.")

    num = 1
    for i in m:
        printToLog("parsing FB profile id " + i + " (" + str(num) + "/" + str(len_m) + ")...")
        prof = 'http://m.facebook.com/' + i + '?v=info'
        if re.search('\?', i):
            prof = 'http://m.facebook.com/' + i + '&v=info'
        
        res = browser.open(prof)
        cont = res.read()
        res.close()

        full_name = ''
        email = ''
        affiliation = ''

        ms = re.search('<strong class="profileName">(.*?)<\/strong>', cont.decode('utf8'))
        if ms:
            full_name = ms.group(1)
        
        ms = re.search('mailto:(.*?)"', cont.decode('utf8'))
        if ms:
            email = ms.group(1).replace("%40", "@")

        ms = re.search('<span class="c mfss">(.*?)<\/span>', cont.decode('utf8'), re.S)
        if ms:
            affiliation = ms.group(1).replace("\n", "").replace("\r", "").strip()
            affiliation = re.sub('<[^>]*>', '', affiliation)
        
        appendToContact("", full_name, "", email, "", affiliation, "", "FB")
        num += 1













def mainLinkedIn():
    global userLinkedIn
    global passwLinkedIn
    
    global LinkedInGID
    
    user = userLinkedIn
    passw = passwLinkedIn
    
    # Set needed modules
    CHandler = urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    browser = urllib.request.build_opener(CHandler)
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
    urllib.request.install_opener(browser)
 
    #Retrieve login form data and initialize the cookies
    printToLog('Initializing LinkedIn parsing...')
    res = browser.open('http://www.linkedin.com/')
 
    #Determine string encoding
    content_type = res.info()['Content-Type'].split('; ')
    encoding = 'utf-8'
    if len(content_type) > 1 and content_type[1].startswith('charset'):
        encoding = content_type[1].split('=')[1]
    html = str(res.read(), 'utf-8')
    res.close()
 
    #add email and password to values
    form_data = []
    form_data.extend( [('session_key', user), ('session_password', passw)] )
    #HACK: urlencode doesn't like strings that aren't encoded with the 'encode' function.
    #Using html.encode(encoding) doesn't help either. why ??
    form_data = [ ( x.encode(encoding), y.encode(encoding) ) for x,y in form_data ]
    data = urllib.parse.urlencode(form_data)
 
    # Login
    printToLog('Logging in to LinkedIn account ' + user)
    # as taken from the action attribute of the login form:
    res = browser.open('http://www.linkedin.com/uas/login-submit', data.encode('ascii'))
    rcode = res.code
    printToLog(rcode)
#    if not re.search('home\.php$', res.url):
#        print('Login Failed')
#        exit(2)
    res.close()
 
    printToLog("Getting LinkedIn group members info...")
    base_page = 'http://www.linkedin.com/groups?viewMembers=&gid=' + LinkedInGID
    res = browser.open(base_page)
    m = re.findall('sik=([0-9]+)', res.url)
    if len(m) == 0:
        printToLog("Error: cannot obtain LinkedIn sik session parameter! Exiting...")
        exit(1)
    base_page = base_page + '&sik=' + str(m[0]) + '&split_page='
    
    m = []
    page = 1
    while True:
        cur_url = base_page + str(page)
        printToLog("fetching LinkedIn group members page: " + cur_url)
        res = browser.open(cur_url)
        parp = res.read()
        m = m + re.findall('"\/profile\/view\?id=([0-9]+)&', parp.decode('utf8'))
        res.close()
        #break
        if re.search('<strong>next', parp.decode('utf8')):
            page += 1
        else:
            break
    # uniqueness:
    m = list(set(m))

    len_m = len(m)
    printToLog(str(len_m) + " LinkedIn profiles found.")
    print(str(len_m) + " LinkedIn profiles found.")

    num = 1
    for i in m:
        printToLog("parsing LinkedIn profile id " + i + " (" + str(num) + "/" + str(len_m) + ")...")

        first_name = ''
        last_name = ''
        full_name = ''
        linkedin_name = ''
        email = ''
        affiliation = ''

        for j in range(1, 3):
            prof = 'http://www.linkedin.com/profile/view?id=' + i
            res = browser.open(prof)
            cont = res.read()
            res.close()
    
            ms = re.search('<span class="given-name">(.*?)<\/span>', cont.decode('utf8'))
            if ms:
                first_name = ms.group(1)
            else:
                ms = re.search('"formattedInfluencerName":"(.*?)"', cont.decode('utf8'))
                if ms:
                    first_name = ms.group(1)

            ms = re.search('<span class="family-name">(.*?)<\/span>', cont.decode('utf8'))
            if ms:
                last_name = ms.group(1)
            # search by any form of lastName is not reliable!
            
            if first_name != '' or last_name != '':
                break
        
        ms = re.search('mailto:(.*?)"', cont.decode('utf8'))
        if ms:
            email = ms.group(1)

        ms = re.search('<p class="headline-title title" style="display:block">(.*?)<\/p>', cont.decode('utf8'), re.S)
        if ms:
            affiliation = ms.group(1).replace("\n", "").replace("\r", "").strip()
        else:
            ms = re.search('<p class="title" style="display:block">(.*?)<\/p>', cont.decode('utf8'), re.S)
            if ms:
                affiliation = ms.group(1).replace("\n", "").replace("\r", "").strip()
            else:
                ms = re.search('"memberHeadline":"(.*?)"', cont.decode('utf8'), re.S)
                if ms:
                    affiliation = ms.group(1).replace("\n", "").replace("\r", "").strip()
        
        if re.search('\.', last_name):
            linkedin_name = first_name + ' ' + last_name
        else:
            if last_name == '':
                ms = re.search('<title>(.*?)<\/title>', cont.decode('utf8'))
                if ms:
                    temp = ms.group(1).replace(" | LinkedIn", "")
                    if len(temp) > 0 and temp[-1] == '.':
                        linkedin_name = temp
                    else:
                        full_name = temp
            else:
                full_name = first_name + ' ' + last_name

        appendToContact("", full_name, linkedin_name, email, "", affiliation, "", "LinkedIn")
        num += 1












class Spreadsheet(object):
    def __init__(self, key):
        super(Spreadsheet, self).__init__()
        self.key = key

class Client(object):
    def __init__(self, email, password):
        super(Client, self).__init__()
        self.email = email
        self.password = password

    def _get_auth_token(self, email, password, source, service):
        url = "https://www.google.com/accounts/ClientLogin"
        params = {
            "Email": email, "Passwd": password,
            "service": service,
            "accountType": "HOSTED_OR_GOOGLE",
            "source": source
        }
        req = urllib.request.Request(url, urllib.parse.urlencode(params).encode('ascii'))
        return re.findall(r"Auth=(.*)", urllib.request.urlopen(req).read().decode('utf8'))[0]

    def get_auth_token(self):
        source = type(self).__name__
        return self._get_auth_token(self.email, self.password, source, service="wise")

    def download(self, spreadsheet, gid=0, format="csv"):
        url_format = "https://spreadsheets.google.com/feeds/download/spreadsheets/Export?key=%s&exportFormat=%s&gid=%i"
        headers = {
            "Authorization": "GoogleLogin auth=" + self.get_auth_token(),
            "GData-Version": "3.0"
        }
        req = urllib.request.Request(url_format % (spreadsheet.key, format, gid), headers=headers)
        return urllib.request.urlopen(req)


def mainWeb():
    global userWeb
    global passwWeb
    
    global GoogleSpreadsheetKey
    
    user = userWeb
    passw = passwWeb

    printToLog('Initializing Web doc parsing...')
    # Create client and spreadsheet objects
    gs = Client(user, passw)
    ss = Spreadsheet(GoogleSpreadsheetKey)

    # Request a file-like object containing the spreadsheet's contents
    csv_file = gs.download(ss)
    encoded_csv_file = codecs.EncodedFile(csv_file, data_encoding='utf-8')

    # Parse as CSV and print the rows
    num = 1

    for row in csv.reader(map(bytes.decode, csv_file)):
        if row[0] != "Timestamp":
            printToLog("parsing Web doc row " + str(num) + "...")
            appendToContact(row[0], row[1], "", row[2], row[3], row[4], row[5], "Web")
            num += 1
    
    num -= 1
    printToLog(str(num) + " Web doc entries found.")
    print(str(num) + " Web doc entries found.")
    
    







def mainTwitter():
    global TwitterScreenName

    num = 1
    follower_cursors = tweepy.Cursor(tweepy.api.followers, id = TwitterScreenName)
    for follower_cursor in follower_cursors.items():
        printToLog("parsing Twitter follower with screen_name " + follower_cursor.screen_name + " (" + str(num) + ")...")

        full_name = ''
        affiliation = ''
        
        # all the fields from a Twitter profile are described here: https://dev.twitter.com/docs/api/1.1/get/users/lookup        
        if str(follower_cursor.name) != "None":
            full_name = str(follower_cursor.name).replace("\n", "").replace("\r", "").strip()      
                
        if str(follower_cursor.description) != "None":
            affiliation = str(follower_cursor.description).replace("\n", "").replace("\r", "").strip()
        if str(follower_cursor.location) != "None":
            affiliation += " (" + str(follower_cursor.location).replace("\n", "").replace("\r", "").strip() + ")"

        num += 1
        appendToContact("", full_name, "", "", "", affiliation, "", "Twitter")

    num -= 1
    printToLog(str(num) + " Twitter followers found.")
    print(str(num) + " Twitter followers found.")
      
                        
  
  
    
        











def appendToContact(timestamp, full_name, linkedin_name, email, why_join, affiliation, others, group):
    global contact_info
    global contact_info_linkedin
    
    timestamp = timestamp.replace("\n", "").replace("\r", "").strip()
    if isinstance(full_name, str):
        full_name = full_name.replace("\n", "").replace("\r", "").strip().title().replace(".", "")
    else:
        full_name = full_name.decode('utf8').replace("\n", "").replace("\r", "").strip().title().replace(".", "")
    linkedin_name = linkedin_name.replace("\n", "").replace("\r", "").strip().title()
    email = email.replace("\n", "").replace("\r", "").strip().lower()
    why_join = why_join.replace("\n", "").replace("\r", "").strip()
    affiliation = affiliation.replace("\n", "").replace("\r", "").strip()
    others = others.replace("\n", "").replace("\r", "").strip()
    
    contact_id = ''
    if full_name != '':
        temp = full_name.split(' ')
        if len(temp) < 2:
            if len(full_name) > 1:
                contact_id = full_name
            if linkedin_name == '':
                linkedin_name = full_name[0] + '.'
        elif len(temp) == 2:
            if len(temp[1]) > 1:
                contact_id = temp[0] + temp[1]
            if linkedin_name == '':
                linkedin_name = temp[0] + ' ' + temp[1][0] + '.'
        elif len(temp) > 2:
            dummy1 = temp[1]
            dummy2 = temp[1] + ' '
            if re.search('\(\)', temp[1]) or len(temp[1]) < 2:
                dummy1 = ''
                dummy2 = ''
            if len(temp[2]) > 1:
                contact_id = temp[0] + dummy1 + temp[2]
            if linkedin_name == '':
                linkedin_name = temp[0] + ' ' + dummy2 + temp[2][0] + '.'
    
    if contact_id == '':
        full_name = ''
    
    if linkedin_name == '':
        printToLog("Warning: parsing in appendToContact (linkedin_name is empty, other data is " + full_name + ',' + email + ',' + why_join + ',' + affiliation + ',' + others + ")!")
        print("Warning: parsing in appendToContact (linkedin_name is empty, other data is " + full_name + ',' + email + ',' + why_join + ',' + affiliation + ',' + others + ")!")
        return
    
    
    if contact_id != '':
        if contact_id not in contact_info:
            contact_info[contact_id].append(timestamp) #0
            contact_info[contact_id].append(full_name) #1
            contact_info[contact_id].append(linkedin_name) #2
            contact_info[contact_id].append(email) #3
            contact_info[contact_id].append(why_join) #4
            contact_info[contact_id].append(affiliation) #5
            contact_info[contact_id].append(others) #6
            contact_info[contact_id].append(group) #7
        else:
            contact_info[contact_id][7] += ',' + group
            if group == "FB":
                if contact_info[contact_id][1] == "":
                    contact_info[contact_id][1] = full_name
                if contact_info[contact_id][2] == "":
                    contact_info[contact_id][2] = linkedin_name
                if contact_info[contact_id][3] == "":
                    contact_info[contact_id][3] = email
                if contact_info[contact_id][5] == "":
                    contact_info[contact_id][5] = affiliation
            elif group == "LinkedIn":
                contact_info[contact_id][1] = full_name
                contact_info[contact_id][2] = linkedin_name
                if email != "":
                    contact_info[contact_id][3] = email
                if affiliation != "":
                    contact_info[contact_id][5] = affiliation
            elif group == "Web":
                if contact_info[contact_id][0] == "":
                    contact_info[contact_id][0] = timestamp
                if contact_info[contact_id][1] == "":
                    contact_info[contact_id][1] = full_name
                if contact_info[contact_id][2] == "":
                    contact_info[contact_id][2] = linkedin_name
                if contact_info[contact_id][3] == "":
                    contact_info[contact_id][3] = email
                if contact_info[contact_id][4] == "":
                    contact_info[contact_id][4] = why_join
                if contact_info[contact_id][5] == "":
                    contact_info[contact_id][5] = affiliation
                if contact_info[contact_id][6] == "":
                    contact_info[contact_id][6] = others
            elif group == "Twitter":
                if contact_info[contact_id][1] == "":
                    contact_info[contact_id][1] = full_name
                if contact_info[contact_id][2] == "":
                    contact_info[contact_id][2] = linkedin_name
                if contact_info[contact_id][5] == "":
                    contact_info[contact_id][5] = affiliation
    else:
        if linkedin_name not in contact_info_linkedin:
            contact_info_linkedin[linkedin_name].append(timestamp) #0
            contact_info_linkedin[linkedin_name].append(full_name) #1
            contact_info_linkedin[linkedin_name].append(linkedin_name) #2
            contact_info_linkedin[linkedin_name].append(email) #3
            contact_info_linkedin[linkedin_name].append(why_join) #4
            contact_info_linkedin[linkedin_name].append(affiliation) #5
            contact_info_linkedin[linkedin_name].append(others) #6
            contact_info_linkedin[linkedin_name].append(group) #7
        else:
            if contact_info_linkedin[linkedin_name][0] == "":
                contact_info_linkedin[linkedin_name][0] = timestamp
            if contact_info_linkedin[linkedin_name][1] == "":
                contact_info_linkedin[linkedin_name][1] = full_name
            if contact_info_linkedin[linkedin_name][2] == "":
                contact_info_linkedin[linkedin_name][2] = linkedin_name
            if contact_info_linkedin[linkedin_name][3] == "":
                contact_info_linkedin[linkedin_name][3] = email
            if contact_info_linkedin[linkedin_name][4] == "":
                contact_info_linkedin[linkedin_name][4] = why_join
            if contact_info_linkedin[linkedin_name][5] == "":
                contact_info_linkedin[linkedin_name][5] = affiliation
            if contact_info_linkedin[linkedin_name][6] == "":
                contact_info_linkedin[linkedin_name][6] = others






def writeIntoFile():
    global filename
    global contact_info
    global contact_info_linkedin
    
    # merging at the very end:
    for linkedin_name in contact_info_linkedin:
        found = 0
        for contact_id in contact_info:
            if linkedin_name == contact_info[contact_id][2]:
                found = 1
                if contact_info[contact_id][0] == "":
                    contact_info[contact_id][0] = contact_info_linkedin[linkedin_name][0]
                if contact_info[contact_id][1] == "":
                    contact_info[contact_id][1] = contact_info_linkedin[linkedin_name][1]
                if contact_info[contact_id][2] == "":
                    contact_info[contact_id][2] = contact_info_linkedin[linkedin_name][2]
                if contact_info[contact_id][3] == "":
                    contact_info[contact_id][3] = contact_info_linkedin[linkedin_name][3]
                if contact_info[contact_id][4] == "":
                    contact_info[contact_id][4] = contact_info_linkedin[linkedin_name][4]
                if contact_info[contact_id][5] == "":
                    contact_info[contact_id][5] = contact_info_linkedin[linkedin_name][5]
                if contact_info[contact_id][6] == "":
                    contact_info[contact_id][6] = contact_info_linkedin[linkedin_name][6]
                contact_info[contact_id][7] += ',' + contact_info_linkedin[linkedin_name][7]
                break
        
        if found == 0:
            contact_id = linkedin_name
            contact_info[contact_id].append(contact_info_linkedin[linkedin_name][0]) #0
            contact_info[contact_id].append(contact_info_linkedin[linkedin_name][1]) #1
            contact_info[contact_id].append(contact_info_linkedin[linkedin_name][2]) #2
            contact_info[contact_id].append(contact_info_linkedin[linkedin_name][3]) #3
            contact_info[contact_id].append(contact_info_linkedin[linkedin_name][4]) #4
            contact_info[contact_id].append(contact_info_linkedin[linkedin_name][5]) #5
            contact_info[contact_id].append(contact_info_linkedin[linkedin_name][6]) #6
            contact_info[contact_id].append(contact_info_linkedin[linkedin_name][7]) #7

    flog = codecs.open(filename,"a","utf-8-sig")
    flog.write(',Timestamp,Full Name,LinkedIn Name,Email,Why do you want to join IEEE STC-SC?,Affiliation,Others,Groups\n')
    num = 1
    for contact_id in contact_info:
        temp_line = ''
        for field in contact_info[contact_id]:
            if re.search(',', field):
                temp_line += ',' + '"' + field + '"'
            else:
                temp_line += ',' + field
            
        flog.write(str(num) + temp_line + '\n')
        num += 1
    flog.close()













#############################
# ptints a message to log
def printToLog(message):
    global logger 
    logger.info(message)








def usage():
    print('Usage: ' + sys.argv[0])
    sys.exit(1)
 
if __name__ == '__main__':
    filename = filename +'_' + strftime("%Y-%m-%d-%H-%M-%S") + ".csv"

    # setting up logging
    hdlr = logging.FileHandler('member-counting.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    
    printToLog("Starting parsing with:\n" + ' '.join(sys.argv))
    
    passwFB = getpass.getpass("[account 1/3] Please enter your password for " + userFB + " (Facebook account): ")
    passwLinkedIn = getpass.getpass("[account 2/3] Please enter your password for " + userLinkedIn + " (LinkedIn account): ")
    passwWeb = getpass.getpass("[account 3/3] Please enter your password for " + userWeb + " (Google account): ")

    mainFB()
    mainLinkedIn()
    mainWeb()
    #mainTwitter()
    
    writeIntoFile()
    
