import shelve

def shelve_clear(shelve_name):
    sh = shelve.open(shelve_name)
    sh.clear()
    if shelve_name == 'words':
        sh['word_frequencies'] = {}
        sh['longest_page'] = ''
        sh['max_count'] = 0
    else:
        sh['.ics.uci.edu'] = {}
    sh.close() 
    
shelve_clear('words')
shelve_clear('URLS')   
