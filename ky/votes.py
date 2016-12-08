import sys

from billy.scrape.votes import VoteScraper, Vote

#import Image
#import ImageChops


#def crop(image, threshold=0.99):
#    """
#    Crop the leftmost/topmost rows/cols with percentage of white pixel
#    less than threshold.
#    """
#    bbox = [0, 0, image.size[0], image.size[1]]

#    for x in xrange(0, image.size[0]):
#        row = image.crop((x, 0, x + 1, image.size[1]))
#        first = row.getcolors()[0]

#        if first[1] == (255, 255, 255):
#            if first[0] / float(image.size[1]) < threshold:
#                bbox[0] = x
#                break

#    for y in xrange(0, image.size[1]):
#        row = image.crop((0, y, image.size[0], y + 1))
#        first = row.getcolors()[0]

#        if first[1] == (255, 255, 255):
#            if first[0] / float(image.size[0]) < threshold:
#                bbox[1] = y
#                break

#    return image.crop(bbox)


#def get_rect_color(image, rect):
#    box = image.crop(rect)
#    colors = box.getcolors()

#    if len(colors) > 1:
#        raise ValueError("Not a solid color: %r" % colors)

#    return colors[0][1]


#def parse_votes(filename):
#    "Extract votes from roll call images from the KY Senate."
#    image = Image.open(filename)

#    # The vote pages have a variable amount of whitespace around the
#    # top and left that we want to strip
#    image = crop(image)

#    votes = []

#    cols = [365, 885, 1410]
#    for col_x in cols:
#        for row in xrange(0, 13):
#            if col_x == 1410 and row == 12:
#                # Thrid column only has 11 entries
#                continue

#            y = 395 + 50 * row

#            yes_rect = (col_x, y, col_x + 10, y + 15)
#            if get_rect_color(image, yes_rect) == (0, 0, 0):
#                yes = True
#            else:
#                yes = False

#            no_rect = (col_x + 35, y, col_x + 45, y + 15)
#            if get_rect_color(image, no_rect) == (0, 0, 0):
#                no = True
#            else:
#                no = False

#            if yes and no:
#                raise ValueError("Double vote")

#            if yes:
#                votes.append('yes')
#            elif no:
#                votes.append('no')
#            else:
#                votes.append('other')

#    return votes


class KYVoteScraper(VoteScraper):
    jurisdiction = 'ky'

    def scrape(self, chamber, session):
        pass
