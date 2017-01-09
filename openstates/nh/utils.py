import pymssql

def build_legislators(cursor):
    # Build a dict that maps EmployeeID -> Legislator to simplify fetching sponsors and votes
    # Note: Legislators can sponsor bills or vote then become inactive mid-session, 
    # so don't filter by Active
    legislators = {}
    
    cursor.execute("SELECT PersonID, Employeeno, FirstName, LastName, MiddleName, LegislativeBody, District FROM Legislators")
    for row in cursor.fetchall():
        #Votes go by employeeNo not PersonId, so index on that.
        legislators[ row['Employeeno'] ] = row

    return legislators


def legislator_name(legislator):
    # Turn an NH database Legislator row into an english name
    return ' '.join(filter(None,[legislator['FirstName'].strip(), legislator['MiddleName'].strip(), legislator['LastName'].strip()]))

def db_cursor():
    db_user = 'publicuser'
    db_password = 'PublicAccess'
    db_address = '216.177.20.245'
    db_name = 'NHLegislatureDB'        
    
    conn = pymssql.connect(db_address, db_user, db_password, db_name)
    return conn.cursor(as_dict=True)