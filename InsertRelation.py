# Import necessary libraries
from neo4j import GraphDatabase
import pandas as pd
from datetime import datetime, timedelta

def main():
    # Neo4j connection details
    URI = "bolt://3.226.239.114:7687"
    AUTH = ("neo4j", "valve-jam-regulations")

    # Establish Neo4j connection
    driver = GraphDatabase.driver(URI, auth=AUTH)

    # Read CSV file
    df = pd.read_csv('tgv_cleaned.csv', sep=';')

    # Group data by date and train number
    grouped_all = df.groupby(['DATE', 'TRAIN_NO'])

    # Prepare data for insertion
    operations = prepare_operations(grouped_all)

    # Insert data into Neo4j
    insert_data(driver, operations)

def prepare_operations(grouped_df):
    operations = []  # List to store operations
    for (date, train), values in grouped_df:  # Iterate over groups of data
        list_com = []  # List to store train stops
        for _, row in values.iterrows():  # Iterate over rows of data in each group
            # Check for departure and arrival times
            if 'Heure_depart' in row and 'Heure_arrivee' in row:
                if row['Heure_depart'] > row['Heure_arrivee']:  # Check if journey is overnight
                    list_com.append((row['Origine IATA'], row['Heure_depart'], 0))  # Add origin with departure indicator
                    list_com.append((row['Destination IATA'], row['Heure_arrivee'], 1))  # Add destination with arrival indicator
                else:
                    list_com.append((row['Origine IATA'], row['Heure_depart'], 0))  # Add origin with departure indicator
                    list_com.append((row['Destination IATA'], row['Heure_arrivee'], 0))  # Add destination with departure indicator
        # Sort stops by indicator and then by time
        list_com = sorted(list_com, key=lambda x: (x[2], x[1]))
        operations.append((train, date, list_com))  # Add operations for this train and date

    # Filter out operations with no data
    operations = [(train, date, sublist) for train, date, sublist in operations if sublist]

    return flatten_operations(operations)

def flatten_operations(operations):
    flattened_operations = []  # List to store flattened operations
    for train, date, sublist in operations:  # Iterate over operations
        for i in range(len(sublist) - 1):  # Iterate over stops
            iataO = sublist[i][0]  
            iataD = sublist[i + 1][0]  
            depart = sublist[i][1]  
            arrive = sublist[i + 1][1]  
            idtrain = train  
            date_initiale = datetime.strptime(date, '%d/%m/%Y')  # Convert date to datetime object
            date_suivante = date_initiale + timedelta(days=1)  # Calculate next date
            nouvelle_date_str = date_suivante.strftime('%d/%m/%Y')  # Convert next date to string format

            # Add operations for different departure and arrival situations
            if sublist[i][2] == 1 and sublist[i + 1][2] == 1:  
                flattened_operations.append((iataO, iataD, idtrain, nouvelle_date_str, nouvelle_date_str, depart, arrive))
            elif sublist[i][2] == 1 and sublist[i + 1][2] == 0:  
                flattened_operations.append((iataO, iataD, idtrain, nouvelle_date_str, date, depart, arrive))
            elif sublist[i][2] == 0 and sublist[i + 1][2] == 1:  
                flattened_operations.append((iataO, iataD, idtrain, date, nouvelle_date_str, depart, arrive))
            else:  
                flattened_operations.append((iataO, iataD, idtrain, date, date, depart, arrive))

    return flattened_operations

def insert_data(driver, operations):
    batch_size = 1000  # Batch size for batch operations
    with driver.session() as session:  # Open Neo4j session
        for i in range(0, len(operations), batch_size):  # Iterate over operations in batches
            batch_data = operations[i:i + batch_size]  # Select current batch
            session.write_transaction(create_relations, batch_data)  # Execute insertion transaction

def create_relations(tx, data):
    # Cypher query to create relationships between stations
    query = '''MATCH (g1:Gare {iata: $iataO}), (g2:Gare {iata: $iataD})
               MERGE (g1)-[:MOOVE {numtrain: $idtrain, datedepart: $datetrain, datearrive: $datetrain2, hdepart: $depart, harrive: $arrive}]->(g2)'''
    for iataO, iataD, idtrain, datetrain, datetrain2, depart, arrive in data:  # Iterate over data to insert
        # Execute the query
        tx.run(query, iataO=iataO, iataD=iataD, idtrain=idtrain, datetrain=datetrain, datetrain2=datetrain2,
               depart=depart, arrive=arrive)

if __name__ == "__main__":
    main()
