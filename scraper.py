import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

#TODO: Collect analytics on raw_respons content:
#   - Unique pages found (Just count all pages crawled; already ignoring URL fragments)
#   - Longest page in terms of words (Extract content from HTML and count length; keep track of max)
#   - 
def extract_next_links(url, resp):
    links = []
    stat_string = str(resp.status)
    # Check for correct status and useful response objects
    if resp.raw_response is not None and (stat_string == "200" or "6" in stat_string or "3" in stat_string):
        html_main = BeautifulSoup(resp.raw_response.content, 'html.parser')
        # Retrive all anchor tags in HTML
        for anchor in html_main.find_all('a'):
            link = anchor.get('href')
            # Check for basic domain rules; allow subdomains and also discard empty links (href = "#")
            if is_valid(link) and link != "#":       
                link = link.split("#")[0]
                # Discard URL fragments
                if link not in links:             
                    links.append(link)
    return links

def is_valid(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
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
            or re.match(r"https?://today[.]uci[.]edu/department/information_computer_sciences(\/[A-Za-z0-9\-\._~:\/\?#\[\]@!$&'\(\)\*\+,;\=]*)?", url))

    except TypeError:
        print ("TypeError for ", parsed)
        raise