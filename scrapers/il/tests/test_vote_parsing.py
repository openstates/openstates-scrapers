from il.bills import find_columns_and_parse

TEST_LINES1 = [
    "E   Acevedo        Y   Davis,Monique   Y   Jefferson        Y   Reboletti",
    "Y   Arroyo         Y   Davis,William   Y   Joyce            N   Reis",
    "Y   Bassi          Y   DeLuca          N   Kosel            Y   Reitz",
    "N   Beaubien       Y   Dugan           Y   Lang             Y   Riley",
    "Y   Beiser         Y   Dunkin          N   Leitch           Y   Rita",
    "E   Bellock        N   Durkin          Y   Lyons            Y   Rose",
]
TEST_LINES2 = [
    "Y    Althoff     Y    Dillard     N   Lauzen        NV   Righter",
    "NV   Bivins      Y    Forby       Y   Lightford     P    Risinger",
    "Y    Bomke       Y    Frerichs    Y   Link          Y    Rutherford",
    "Y    Bond        Y    Garrett     Y   Luechtefeld   Y    Sandoval",
    "N    Brady       NV   Haine       Y   Maloney       Y    Schoenberg",
    "N    Burzynski   Y    Halvorson   Y   Martinez      Y    Silverstein",
    "Y    Clayborne   Y    Harmon      Y   Meeks         Y    Steans",
    "Y    Collins     Y    Hendon      Y   Millner       Y    Sullivan",
    "NV   Cronin      Y    Holmes      Y   Munoz         P    Syverson",
    "Y    Crotty      Y    Hultgren    N   Murphy        Y    Trotter",
    "Y    Cullerton   Y    Hunter      Y   Noland        Y    Viverito",
    "Y    Dahl        Y    Jacobs      Y   Pankau        Y    Watson",
    "Y    DeLeo       Y    Jones, J.   P   Peterson      Y    Wilhelmi",
    "Y    Delgado     Y    Koehler     Y   Radogno       Y    Mr. President",
    "Y    Demuzio     Y    Kotowski    Y   Raoul",
]

TEST_LINES3 = [
    "Y    Althoff       Y    Haine         Y    Lightford     Y   Raoul",
    "Y    Bivins        Y    Harmon        NV   Link          Y   Rezin",
    "Y    Bomke         Y    Holmes        Y    Luechtefeld   Y   Righter",
    "Y    Brady         Y    Hunter        Y    Maloney       Y   Sandack",
    "Y    Clayborne     Y    Hutchinson    Y    Martinez      Y   Sandoval",
    "Y    Collins, A.   N    Jacobs        Y    McCann        Y   Schmidt",
    "Y    Collins, J.   Y    Johnson, C.   Y    McCarter      Y   Schoenberg",
    "Y    Crotty        Y    Johnson, T.   Y    Meeks         Y   Silverstein",
    "Y    Cultra        Y    Jones, E.     Y    Millner       Y   Steans",
    "Y    Delgado       Y    Jones, J.     Y    Mulroe        Y   Sullivan",
    "Y    Dillard       Y    Koehler       Y    Muñoz         Y   Syverson",
    "Y    Duffy         NV   Kotowski      Y    Murphy        Y   Trotter",
    "Y    Forby         Y    LaHood        Y    Noland        Y   Wilhelmi",
    "Y    Frerichs      Y    Landek        Y    Pankau        Y   Mr. President",
    "NV   Garrett       Y    Lauzen        Y    Radogno",
]


def test_find_and_parse1():
    d = find_columns_and_parse(TEST_LINES1)
    assert d["Acevedo"] == "E"
    assert d["Davis,William"] == "Y"
    assert d["Dunkin"] == "Y"
    assert d["Durkin"] == "N"
    assert d["Lyons"] == "Y"
    assert d["Reis"] == "N"


def test_find_and_parse2():
    d = find_columns_and_parse(TEST_LINES2)
    assert d["Cronin"] == "NV"
    assert d["Holmes"] == "Y"
    assert d["Murphy"] == "N"
    assert d["Mr. President"] == "Y"
    assert d["Peterson"] == "P"


def test_find_and_parse3():
    d = find_columns_and_parse(TEST_LINES3)
    assert d["Collins, A."] == "Y"
    assert d["Garrett"] == "NV"
    assert d["Muñoz"] == "Y"
    assert d["Syverson"] == "Y"
    assert d["Link"] == "NV"
