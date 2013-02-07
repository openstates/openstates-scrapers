'''
This module parses the pdb of assembly contact info to get each member's
party affiliation. It's prinst out a matching dictionary that can be
(shudder) pasted into the NY legislator scraper. It's output needs to be
double checked though, because it uses fuzzy matching to match names on the
sheet to each legislator's full_name.
'''
import re
import lxml.html
import difflib

from billy.scrape.utils import convert_pdf


def getname(string):
    _, string = re.split(r'\s*\d+\s+', string, 1)
    name, _ = re.split(r'\.{4,}', string, 1)
    return name.strip()


def main():
    html = convert_pdf('openstates/ny/scripts/assembly_parties.pdf')
    doc = lxml.html.fromstring(html)
    dems = doc.xpath('//text[@font="4"]/b/text()')
    dems = map(getname, dems)
    repubs = doc.xpath('//text[@font="5"]/i/b/text()')
    repubs = map(getname, repubs)

    name_to_party = {}
    for list_, party in ((dems, 'Democratic'), (repubs, 'Republican')):
        for name in list_:
            print name, 'matched',
            try:
                full_name = difflib.get_close_matches(name, legs).pop(0)
            except IndexError:
                print 'NO MATCH FOUND'
                continue
            print full_name, ':: party = ', party
            name_to_party[full_name] = party
            print party

    # import pprint
    # pprint.pprint(name_to_party)

    print 'party_dict = {'
    it = iter(name_to_party.items())
    while True:

        try:
            # Col 1
            full_name1, party1 = next(it)
            full_name2, party2 = next(it)

            print ('\n    %r: %r,' % (full_name1, party1)).ljust(45),
            print ('%r: %r,' % (full_name2, party2))
        except StopIteration:
            break

    print '    }'

legs = ['Abbate, Jr., Peter',
 'Abinanti, Thomas',
 'Arroyo, Carmen',
 'Aubry, Jeffrion',
 'Barclay, William',
 'Barrett, Didi',
 'Barron, Inez',
 'Benedetto, Michael',
 'Blankenbush, Ken',
 'Borelli, Joseph',
 'Boyland, Jr., William',
 'Braunstein, Edward',
 'Brennan, James',
 'Brindisi, Anthony',
 'Bronson, Harry',
 'Brook-Krasny, Alec',
 'Buchwald, David',
 'Butler, Marc',
 'Cahill, Kevin',
 'Camara, Karim',
 'Castro, Nelson',
 'Ceretto, John',
 'Clark, Barbara',
 'Colton, William',
 'Cook, Vivian',
 'Corwin, Jane',
 'Crespo, Marcos',
 'Crouch, Clifford',
 'Curran, Brian',
 'Cusick, Michael',
 'Cymbrowitz, Steven',
 'DenDekker, Michael',
 'Dinowitz, Jeffrey',
 'DiPietro, David',
 'Duprey, Janet',
 'Englebright, Steve',
 'Espinal, Jr., Rafael',
 'Fahy, Patricia',
 'Farrell, Jr., Herman',
 'Finch, Gary',
 'Fitzpatrick, Michael',
 'Friend, Christopher',
 'Gabryszak, Dennis',
 'Galef, Sandy',
 'Gantt, David',
 'Garbarino, Andrew',
 'Gibson, Vanessa',
 'Giglio, Joseph',
 'Gjonaj, Mark',
 'Glick, Deborah',
 'Goldfeder, Phillip',
 'Goodell, Andy',
 'Gottfried, Richard',
 'Graf, Al',
 'Gunther, Aileen',
 'Hawley, Stephen',
 'Heastie, Carl',
 'Hennessey, Edward',
 'Hevesi, Andrew',
 'Hikind, Dov',
 'Hooper, Earlene',
 'Jacobs, Rhoda',
 'Jaffee, Ellen',
 'Johns, Mark',
 'Jordan, Tony',
 'Katz, Steve',
 'Kavanagh, Brian',
 'Kearns, Michael',
 'Kellner, Micah',
 'Kim, Ron',
 'Kolb, Brian M.',
 'Lalor, Kieran Michael',
 'Lavine, Charles',
 'Lentol, Joseph',
 'Lifton, Barbara',
 'Lopez, Peter',
 'Lopez, Vito',
 'Losquadro, Dan',
 'Lupardo, Donna',
 'Lupinacci, Chad',
 'Magee, William',
 'Magnarelli, William',
 'Maisel, Alan',
 'Malliotakis, Nicole',
 'Markey, Margaret',
 'Mayer, Shelley',
 'McDonald, III, John',
 'McDonough, David',
 'McKevitt, Tom',
 'McLaughlin, Steven',
 'Miller, Michael',
 'Millman, Joan',
 'Montesano, Michael',
 'Morelle, Joseph',
 'Mosley, Walter',
 'Moya, Francisco',
 'Nojay, Bill',
 'Nolan, Catherine',
 "O'Donnell, Daniel",
 'Oaks, Bob',
 u'Ortiz, F\xe9lix',
 'Otis, Steven',
 'Palmesano, Philip',
 'Paulin, Amy',
 'Peoples-Stokes, Crystal',
 'Perry, N. Nick',
 'Pretlow, J. Gary',
 'Quart, Dan',
 'Ra, Edward',
 'Rabbitt, Annie',
 'Raia, Andrew',
 'Ramos, Phil',
 'Reilich, Bill',
 u'Rivera, Jos\xe9',
 'Roberts, Samuel',
 'Robinson, Annette',
 'Rodriguez, Robert',
 'Rosa, Gabriela',
 'Rosenthal, Linda',
 'Rozic, Nily',
 'Russell, Addie',
 'Ryan, Sean',
 'Saladino, Joseph',
 'Santabarbara, Angelo',
 'Scarborough, William',
 'Schimel, Michelle',
 'Schimminger, Robin',
 'Sepulveda, Luis',
 'Silver, Sheldon',
 'Simanowitz, Michael',
 'Simotas, Aravella',
 'Skartados, Frank',
 'Skoufis, James',
 'Solages, Michaelle',
 'Stec, Dan',
 'Steck, Phil',
 'Stevenson, Eric',
 'Stirpe, Al',
 'Sweeney, Robert',
 'Tedisco, James',
 'Tenney, Claudia',
 'Thiele, Jr., Fred',
 'Titone, Matthew',
 'Titus, Michele',
 'Walter, Raymond',
 'Weinstein, Helene',
 'Weisenberg, Harvey',
 'Weprin, David',
 'Wright, Keith L.T.',
 'Zebrowski, Kenneth']


if __name__ == '__main__':
    main()
