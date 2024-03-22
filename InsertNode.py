from neo4j import GraphDatabase
import pandas as pd

# Neo4j connection details
# Definition of Neo4j server URI and authentication
URI = "bolt://3.226.239.114:7687"
AUTH = ("neo4j", "valve-jam-regulations")

def main():
    # Establishing connection to Neo4j
    driver = GraphDatabase.driver(URI, auth=AUTH)

    # Reading the CSV file
    df = pd.read_csv('tgv_cleaned.csv', sep=';')
    
    # Grouping by Origin and Destination and retrieving the second occurrence
    origins = df.groupby('Origine IATA').nth(1).reset_index()
    destinations = df.groupby('Destination IATA').nth(1).reset_index()

    # Merging Origin and Destination data to form a dictionary of stations
    station_dict = {**dict(zip(origins['Origine IATA'], origins['Origine'])), 
                    **dict(zip(destinations['Destination IATA'], destinations['Destination']))}

    # Creating stations in Neo4j
    with driver.session() as session:
        for IATA, name in station_dict.items():
            session.write_transaction(create_station, name, IATA)

# Function to create a station in Neo4j
def create_station(tx, name, IATA):
    query = "MERGE (:Gare {nom: $name, iata: $IATA})"
    tx.run(query, name=name, IATA=IATA)

if __name__ == "__main__":
    main()

