import re
from urllib.parse import urlparse
import urllib.robotparser
from time import sleep
import operator

# Additional Libraries
from bs4 import BeautifulSoup
from textblob import TextBlob

# Personally written lib
from stopwords import stopwords

import shelve

def discard_url_traps(url):
    new_url = urlparse(url)                
    clean_url = url.replace(new_url.fragment, "")       # Discard URL fragments
    clean_url = clean_url.replace("?" + new_url.query, "")    # Discard URL query params to avoid traps
    return clean_url

def discard_scheme(url):
    curr_url = urlparse(url)
    clean_url = url.replace(curr_url.scheme + "://", "")    #Discard Scheme
    return clean_url

def strip_stop_words(page_words):
    stopset = set()
    pageset = set()
    for word in stopwords:
        stopset.add(word)
    for word in page_words:
        pageset.add(word)
    return pageset - stopset

def politeness(url):
    url_parsed = urlparse(url)
    nice_bot = urllib.robotparser.RobotFileParser(url_parsed.scheme + "://" + url_parsed.netloc + "/robots.txt")
    nice_bot.read()
    return nice_bot

def URL_tracking(url):
    # Track unique URLS
    f = open("reports/uniqueurl.txt", "r")
    URL_set = {URL.replace("\n", "") for URL in f}
    f.close()
    init_set_size = len(URL_set)
    URL_set.add(discard_scheme(url))
    if init_set_size < len(URL_set):
        f = open("reports/uniqueurl.txt", "w")
        for page in URL_set:
            f.write(page + "\n")
        f.close()

    # Track subdomains and unique pages within them
    URL_DB = shelve.open("URLS")
    url_parsed = urlparse(url)
    url_netloc = url_parsed.netloc
    url_netloc = url_netloc.replace("www.","") #discard www
    ics_domain = ".ics.uci.edu"
    if ics_domain in url_netloc and url_netloc != ics_domain:
        subdomain_dict = URL_DB[ics_domain]
        if url_netloc in subdomain_dict:
            subdomain_dict[url_netloc] += 1
        else:
            subdomain_dict[url_netloc] = 1
        URL_DB[ics_domain] = subdomain_dict

    # Write subdomains sorted in alphabetical order to subdomains.txt
    ics_subdomains = []
    for main, sub in URL_DB[ics_domain].items():
        ics_subdomains.append((main,sub))
    ics_subdomains = sorted(ics_subdomains, key=operator.itemgetter(0))
    f = open("reports/subdomains.txt", "w")
    for sub,pages in ics_subdomains:
        f.write(sub + ", " + str(pages) + "\n")
    f.close()
    URL_DB.close()

def word_tracking(url, page_words):
    words_DB = shelve.open("words")
    # Remove stop words from page words
    destopped_words = strip_stop_words(page_words)
    wordiest_line = ""

    # Determine if page has most words
    with open("reports/wordiestpage.txt", "r") as f:
        wordiest_line = f.readline()
        f.close()
    line_split = wordiest_line.split()
    max_word_count = int(line_split[1])
    new_word_count = len(destopped_words)
    if new_word_count > max_word_count:
        words_DB["max_count"] = new_word_count
        words_DB["longest_page"] = url
        with open("reports/wordiestpage.txt", "w") as f:
            f.write(url + " " + str(new_word_count))
            f.close()

    # Determine top 50 words
    current_word_freq = words_DB["word_frequencies"]
    for word in destopped_words:
        if word in current_word_freq:
            current_word_freq[word] += 1
        else:
            current_word_freq[word] = 0
    words_DB["word_frequencies"] = current_word_freq
    with open("reports/top50words.txt", "w") as f:
        i = 0
        top_words = sorted(current_word_freq.items(), key=operator.itemgetter(1), reverse=True)
        for word, freq in top_words:
            if i >= 50:
                break
            f.write(word+ " " + str(freq) + "\n")
            i += 1
        f.close()
    words_DB.close()

def scraper(url, resp):
    valid_links = []
    stat_string = str(resp.status)
    if stat_string == "200" or stat_string[0] == "3":
        robot_rules = politeness(url)
        if robot_rules is not None:
            if robot_rules.request_rate("*") is not None:
                sleep(robot_rules.request_rate("*").seconds / robot_rules.request_rate("*").requests)
            if robot_rules.crawl_delay("*") is not None:
                sleep(robot_rules.crawl_delay("*"))
        for link in extract_next_links(url, resp):
            # Check for basic domain rules; allow subdomains and also discard empty links (href = "#")
            if is_valid(link) and link != "#": 
                if robot_rules is not None:
                    if robot_rules.can_fetch("*", link):
                        valid_links.append(link)
                else:
                    valid_links.append(link)
    return valid_links

def extract_next_links(url, resp):
    links = []
    if resp.raw_response is not None and resp.raw_response.apparent_encoding is not None:
        URL_tracking(url)     # Write link to file
        html_main = BeautifulSoup(resp.raw_response.content, 'html.parser')
        page_text = html_main.get_text()
        page_blob = None
        if page_text is not None:
            page_blob = TextBlob(page_text)
        if page_blob is not None and len(page_blob.sentences) > 8:
            word_tracking(discard_scheme(url), page_blob.words)
            for anchor in html_main.find_all('a'):      # Retrive all anchor tags in HTML
                link = anchor.get('href')
                if is_valid(link):
                    clean_link = discard_url_traps(link)
                    if clean_link not in links:             
                        links.append(clean_link)
    return links

def is_valid(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpeg|jpg|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()) \
            and (re.match(r"https?://([a-z0-9]+[.])*ics[.]uci[.]edu(\/[A-Za-z0-9\-\._~:\/\?#\[\]@!$&'\(\)\*\+,;\=]*)?", url) \
            or re.match(r"https?://([a-z0-9]+[.])*cs[.]uci[.]edu(\/[A-Za-z0-9\-\._~:\/\?#\[\]@!$&'\(\)\*\+,;\=]*)?", url) \
            or re.match(r"https?://([a-z0-9]+[.])*informatics[.]uci[.]edu(\/[A-Za-z0-9\-\._~:\/\?#\[\]@!$&'\(\)\*\+,;\=]*)?", url) \
            or re.match(r"https?://today[.]uci[.]edu/department/information_computer_sciences(\/[A-Za-z0-9\-\._~:\/\?#\[\]@!$&'\(\)\*\+,;\=]*)?", url)) \
            and "replytocom" not in url and "pdf" not in url and "event" not in url and "calendar" not in url and "download" not in url

    except TypeError:
        print ("TypeError for ", parsed)
        raise