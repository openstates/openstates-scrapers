""" Basic functions for drawing SVG maps of the US """

import sys

def rgb_to_hex(r,g,b):
    """ Convert r,g,b values to a #abcdef hex string """
    return '#%.2x%.2x%.2x' % (r,g,b)


def hex_to_rgb(hex):
    """ Convert #abcdef hex distribution to r,g,b triplet """
    return (int(hex[1:3], 16), int(hex[3:5], 16), int(hex[5:7],16))


def colorized_svg(mapping, border_color='#000000', default_color='#cccccc',
                  infile='svg/templatized_usa.svg'):
    """ Create a custom colorized map of the United States in SVG format.

        mapping is a mapping from color to a list of one or more states
        (reversed this way so that it is easier to color many states one color)
    """

    uncolored = set(('AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL',
                     'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
                     'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
                     'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
                     'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
                     'WY'))
    substs = {'border_color':border_color}

    # read the SVG file
    data = open(infile).read()

    # replace colors, removing states as they are colored
    for color, states in mapping.iteritems():
        uncolored.difference_update(states)
        for state in states:
            substs['%s_COLOR' % state] = color

    # default color remaining states
    for state in uncolored:
        substs['%s_COLOR' % state] = default_color

    return data % substs

def colorized_range_svg(mapping, low_color=(0,0,0), high_color=(255,255,255)):

    color_mapping = {}

    # mapping is a mapping from float values to states
    for value, states in mapping.iteritems():
        color = rgb_to_hex(low_color[0]+high_color[0]*value,
                           low_color[1]+high_color[1]*value,
                           low_color[2]+high_color[2]*value)

        color_mapping[color] = states

    return colorized_svg(color_mapping)


def svg_to_png(svgdata, output=sys.stdout, width=None, height=None):
    """ Render raw SVG data to PNG """

    import rsvg
    import cairo

    svg = rsvg.Handle(data=svgdata)

    if not width and not height:
        width = svg.props.width
        height = svg.props.height
        ratio = 1
    elif width:
        ratio = float(width) / svg.props.width
        height = int(ratio * svg.props.height)
    elif height:
        ratio = float(height) / svg.props.height
        width = int(ratio * svg.props.width)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(surface)
    context.scale(ratio, ratio)
    svg.render_cairo(context)
    surface.write_to_png(output)


def test_gradient_map():
    """ generate a test gradient map """

    from collections import defaultdict
    from random import random
    allstates = ('AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL',
                     'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
                     'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
                     'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
                     'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
                     'WY')

    mapping = defaultdict(list)

    for state in allstates:
        mapping[random()].append(state)

    return colorized_range_svg(mapping, low_color=(0,0,0), high_color=(0,0,255))

if __name__ == '__main__':
    # generate a map resembling the 2008 election results
    redstates = ('AL', 'AK', 'AZ', 'AR', 'GA', 'KS', 'KY', 'LA', 'MO', 'MS',
                 'OK', 'MT', 'NE', 'ND', 'SC', 'SD', 'TN', 'TX', 'UT', 'WV',
                 'WY')

    #svg_to_png(colorized_svg({'#ff0000': redstates}, default_color='#0000ff'))

    svg_to_png(test_gradient_map())
