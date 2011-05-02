import sys

import Image
import ImageChops


def get_rect_color(image, rect):
    box = image.crop(rect)
    colors = box.getcolors()

    if len(colors) > 1:
        raise ValueError("Not a solid color: %r" % colors)

    return colors[0][1]


def parse_votes(filename):
    "Extract votes from roll call images from the KY Senate."
    image = Image.open(filename)

    # The vote pages have a variable amount of whitespace around the
    # top and left that we want to strip (by cropping to the bounding box
    # of the inverse of the image)
    inverted = ImageChops.invert(image)
    image = image.crop(inverted.getbbox())

    votes = []

    cols = [365, 885, 1410]
    for col_x in cols:
        for row in xrange(0, 13):
            if col_x == 1405 and row == 12:
                # Thrid column only has 11 entries
                continue

            y = 395 + 50 * row

            yes_rect = (col_x, y, col_x + 10, y + 15)
            if get_rect_color(image, yes_rect) == (0, 0, 0):
                yes = True
            else:
                yes = False

            no_rect = (col_x + 35, y, col_x + 45, y + 15)
            if get_rect_color(image, no_rect) == (0, 0, 0):
                no = True
            else:
                no = False

            if yes and no:
                raise ValueError("Double vote")

            if yes:
                votes.append('yes')
            elif no:
                votes.append('no')
            else:
                votes.append('other')

    return votes


if __name__ == '__main__':
    import sys
    print parse_votes(sys.argv[1])
