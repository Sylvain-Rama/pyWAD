import re 

DOOM1_MAP_NAME_REGEX = re.compile(r'^E(?P<episode>[0-9])M(?P<number>[0-9])$')
DOOM2_MAP_NAME_REGEX = re.compile(r'^MAP(?P<number>[0-9]{2})$')