import re

def split_name(full_name):
    m = re.match('(\w+) (\w)\. (\w+)', full_name)
    if m:
        first_name = m.group(1)
        middle_name = m.group(2)
        last_name = m.group(3)
    else:
        first_name = full_name.split(' ')[0]
        last_name = ' '.join(full_name.split(' ')[1:])
        middle_name = ''

    suffix = ''
    if last_name.endswith(', Jr.'):
        last_name = last_name.replace(', Jr.', '')
        suffix = 'Jr.'

    return (first_name, last_name, middle_name, suffix)
