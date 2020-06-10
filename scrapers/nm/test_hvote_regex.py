from collections import defaultdict
import re

# hb1 is relatively normal
hb1 = """
                       NEW MEXICO HOUSE OF REPRESENTATIVES
RCS# 2668                    Forty-Ninth Legislature                         1/19/11
                               FIRST SESSION, 2011                          11:45 AM


                                     HB 1/EC
                                 REP Martinez, W.
                                  FINAL PASSAGE


                  Absent: 4    Yeas: 66    Nays: 0      Excused: 0


  Y   Alcon, E.        Y Ezzell, C. S.    Y   Little, R.       Y   Saavedra, H.
  Y   Anderson, T. A   Y Garcia, M.H.     Y   Lujan, A.        Y   Salazar, N.
  Y   Baldonado, A.    Y Garcia, M.P.     Y   Lujan, Ben       Y   Sandoval, E.
  Y   Bandy, P. C.     Y Garcia, T.A.     Y   Lundstrom, P.    Y   Smith, J. S.
  Y   Begaye, Ray      Y Gentry, N.           Madalena, J. R   Y   Stapleton, S.
  Y   Bratton, D.      Y Gonzales, R.     Y   Maestas, A.      Y   Stewart, M.
  Y   Brown, C. B.     Y Gray, W. J.      Y   Martinez, R.     Y   Strickler, J.
  Y   Cervantes, J.    Y Gutierrez, J.    Y   Martinez, W. K   Y   Taylor T. C.
  Y   Chasey, Gail     Y Hall, J. C.      Y   McMillan, T.     Y   Tripp, D.
  Y   Chavez, D.       Y Hamilton, D.     Y   Miera, R.        Y   Trujillo, J.R.
  Y   Chavez, E.       Y Herrell, Y.      Y   Nunez, A.        Y   Tyler, S. A.
  Y   Chavez, E. H.    Y Irwin, D. G.     Y   O'Neill, B.      Y   Varela, L.
  Y   Cook, Z.J.       Y James,C. D.      Y   Park, A.         Y   Vigil, R. D.
  Y   Crook, A. M.     Y Jeff, S.         Y   Picraux, D.      Y   Wallace, J.
  Y   Dodge, G.        Y King, R.             Powdrell-C, J.   Y   White, J. P.
  Y   Doyle, D.        Y Kintigh, D.      Y   Rehm, W.         Y   Wooley, B.
  Y   Egolf, B.          Larranaga, L.        Roch, D.
  Y   Espinoza, N.     Y Lewis, T.        Y   Rodella, D.




                              CERTIFIED CORRECT TO THE BEST OF OUR KNOWLEDGE



                              ___________________________________ (Speaker)



                              ___________________________________ (Chief Clerk)"""


# has some single-spaced votes, ugh
hb131 = """                     NEW MEXICO HOUSE OF REPRESENTATIVES
RCS# 2811                    Fiftieth Legislature                       2/24/11
                             FIRST SESSION, 2011                       11:41 AM


                                    HB 131
                                  Rep Varela
                                FINAL PASSAGE


               Absent: 0    Yeas: 34     Nays: 34    Excused: 2


  Y Alcon, E.        N Ezzell, C. S.    N  Little, R.        Y Saavedra, H.
 N  Anderson, T. A    Y Garcia, M.H.     Y Lujan, A.      E    Salazar, N.
 N  Baldonado, A.     Y Garcia, M.P.     Y Lujan, Ben        Y Sandoval, E.
 N  Bandy, P. C.      Y Garcia, T.A.     Y Lundstrom, P.    N Smith, J. S.
  Y Begaye, Ray      N Gentry, N.        Y Madalena, J. R    Y Stapleton, S.
 N Bratton, D.        Y Gonzales, R.     Y Maestas, A.       Y Stewart, M.
 N Brown, C. B.      N Gray, W. J.       Y Martinez, R.     N Strickler, J.
  Y Cervantes, J.     Y Gutierrez, J.    Y Martinez, W. K N Taylor T. C.
  Y Chasey, Gail     N Hall, J. C.       Y McMillan, T.     N Tripp, D.
 N Chavez, D.        N Hamilton, D.      Y Miera, R.         Y Trujillo, J.R.
  Y Chavez, E.       N Herrell, Y.      N Nunez, A.         N Tyler, S. A.
  Y Chavez, E.H.   E    Irwin, D. G.     Y O'Neill, B.       Y Varela, L.
 N Cook, Z.J.        N James,C. D.       Y Park, A.          Y Vigil, R. D.
  Y Crook, A. M.     N Jeff, S.         N Picraux, D.       N Wallace, J.
  Y Dodge, G.         Y King, R.        N Powdrell-C, J. N White, J. P.
 N Doyle, D.         N Kintigh, D.       Y Rehm, W.         N Wooley, B.
  Y Egolf, B.        N Larranaga, L.    N Roch, D.
 N Espinoza, N.      N Lewis, T.        N Rodella, D.




                            CERTIFIED CORRECT TO THE BEST OF OUR KNOWLEDGE



                            ___________________________________ (Speaker)



                            ___________________________________ (Chief Clerk)"""


HOUSE_VOTE_RE = re.compile(r"([YNE ])\s+([A-Z][a-z\'].+?)(?=\s[\sNYE])")


def check_regex_against_vote(vote, y, n, a, e):
    counts = defaultdict(int)
    for v in HOUSE_VOTE_RE.findall(vote):
        if "Excused" in v[1]:
            counts = defaultdict(int)
            continue
        counts[v[0]] += 1
    if counts["Y"] != y or counts["N"] != n or counts[" "] != a or counts["E"] != e:
        print(counts)
        for x in HOUSE_VOTE_RE.findall(vote):
            print(" ", x)
    else:
        print("  good")


print("HB1")
check_regex_against_vote(hb1, 66, 0, 4, 0)
print("HB131")
check_regex_against_vote(hb131, 34, 34, 0, 2)
