from neo4j import GraphDatabase
from datetime import datetime,timedelta

class Node:
    """
    Represents a node in the train station graph.
    """
    def __init__(self, name, departure_date, departure_time, arrival_date, arrival_time, train_number, parent=None):
        """
        Initializes a Node object.

        Args:
            name (str): Name of the train station.
            departure_date (str): Departure date.
            departure_time (str): Departure time.
            arrival_date (str): Arrival date.
            arrival_time (str): Arrival time.
            train_number (str): Train number.
            parent (Node, optional): Parent node in the found path.
        """
        self.name = name  
        self.parent = parent  
        self.distance = float('inf')  # Initial distance, used for shortest path calculation
        self.departure_date = departure_date  
        self.departure_time = departure_time 
        self.arrival_date = arrival_date  
        self.arrival_time = arrival_time  
        self.train_number = train_number  

class Neo4jGraph:
    """
    Interface to interact with the Neo4j database.
    """
    def __init__(self, uri, user, password):
        """
        Initializes a connection to the Neo4j database.

        Args:
            uri (str): Database URI.
            user (str): Username to connect.
            password (str): Password to connect.
        """
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Closes the connection to the database."""
        self._driver.close() # Closing the Neo4j driver connection

    
    def get_premiernodes(self, node_name, departure_date, departure_time):
        """
        Retrieves neighboring nodes for a given node, based on departure date and time.

        Args:
            node_name (str): Name of the departing node.
            departure_date (str): Departure date.
            departure_time (str): Departure time.

        Returns:
            list: List of neighboring nodes.
        """
        nodes = []
        with self._driver.session() as session:
            if departure_date is None or departure_time is None:
                return nodes

            result = session.run(
                "MATCH (n:Gare {nom: $name})-[r:MOOVE]->(neighbor:Gare) "
                "WHERE (r.datedepart = $departure_date AND r.hdepart >= $departure_time) "
                "RETURN n.nom AS name, r.datedepart AS departure_date, r.datearrive AS arrival_date, "
                "r.hdepart AS departure_time, r.harrive AS arrival_time, r.numtrain AS train_number "
                "ORDER BY r.datedepart, r.hdepart",
                name=node_name, departure_date=departure_date, departure_time=departure_time)
            
            for record in result: # Looping over the result records
                if record["departure_date"] is None or record["departure_time"] is None or record["arrival_date"] is None or record["arrival_time"] is None:
                    continue  # Skip iteration if any of the required fields is missing
                nodes.append(Node(record["name"], record["departure_date"], record["departure_time"], record["arrival_date"], record["arrival_time"], record["train_number"]))
            
        return nodes

    def get_neighbors(self, node_name, departure_date, departure_time):
        """
        Retrieves neighbors of a given node based on departure date and time.

        Args:
            node_name (str): Name of the departing node.
            departure_date (str): Departure date.
            departure_time (str): Departure time.

        Yields:
            tuple: Pair (neighbor, distance).
        """
        with self._driver.session() as session:
            result = session.run(
                "MATCH (n:Gare {nom: $name})-[r:MOOVE]->(neighbor:Gare) "
                "WHERE (r.datedepart >= $departure_date AND r.hdepart >= $departure_time) "         
                "RETURN neighbor.nom AS name, r.datedepart AS departure_date, r.datearrive AS arrival_date, r.hdepart AS departure_time, r.harrive AS arrival_time, r.numtrain AS train_number "
                "ORDER BY r.datedepart, r.hdepart",
                name=node_name, departure_date=departure_date, departure_time=departure_time)
            for record in result:  # Looping over the result records
                if record["departure_date"] is None or record["departure_time"] is None or record["arrival_date"] is None or record["arrival_time"] is None:
                    continue # Skip iteration if any of the required fields is missing
                
                neighbor = Node(record["name"], record["departure_date"], record["departure_time"], record["arrival_date"], record["arrival_time"], record["train_number"]) # Creating a neighbor node object

                
                next_train_departure = datetime.strptime(neighbor.departure_date + " " + neighbor.departure_time, "%d/%m/%Y %H:%M") # Parsing the next train departure datetime
                current_arrival = datetime.strptime(departure_date + " " + departure_time, "%d/%m/%Y %H:%M") # Parsing the current arrival datetime
                if next_train_departure > current_arrival: # Checking if the next train departure is after the current arrival
                    # Si c'est le cas, on inclut ce voisin potentiel
                    neighbor_distance = self.calculate_duration(departure_date, departure_time, neighbor.arrival_date, neighbor.arrival_time) # Calculating the duration between current departure and neighbor arrival
                    yield neighbor, neighbor_distance # Yielding the neighbor and its distance from the current node
    

    @staticmethod
    def calculate_duration(departure_date, departure_time, arrival_date, arrival_time):
        """
        Calculates the duration between two departure and arrival dates and times.

        Args:
            departure_date (str): Departure date.
            departure_time (str): Departure time.
            arrival_date (str): Arrival date.
            arrival_time (str): Arrival time.

        Returns:
            float: Duration in minutes.
        """
        if departure_time is None or arrival_time is None:
            return 0  # Return 0 if any of the time values is missing
        
        departure_datetime = datetime.strptime(departure_date + " " + departure_time, "%d/%m/%Y %H:%M") # Parsing departure datetime
        arrival_datetime = datetime.strptime(arrival_date + " " + arrival_time, "%d/%m/%Y %H:%M") # Parsing arrival datetime
        
        day_difference = (arrival_datetime.date() - departure_datetime.date()).days # Calculating the difference in days between arrival and departure
        
        if day_difference < 0: # Adjusting arrival datetime if it's before the departure datetime
            arrival_datetime += timedelta(days=-day_difference)
        
       
        next_train_departure = departure_datetime + timedelta(days=day_difference) # Calculating the next train departure datetime
        if arrival_datetime > next_train_departure: # Adjusting arrival datetime if it's after the next train departure
            arrival_datetime = next_train_departure

        return (arrival_datetime - departure_datetime).total_seconds() / 60 # Calculating and returning the duration in minutes

    @staticmethod
    def calculate_total_time(departure_date, departure_time, arrival_date, arrival_time):
        """
        Calculates the total duration between two departure and arrival dates and times.

        Args:
            departure_date (str): Departure date.
            departure_time (str): Departure time.
            arrival_date (str): Arrival date.
            arrival_time (str): Arrival time.

        Returns:
            int: Total duration in minutes.
        """
        departure_datetime = datetime.strptime(departure_date + " " + departure_time, "%d/%m/%Y %H:%M")  # Parsing departure datetime
        arrival_datetime = datetime.strptime(arrival_date + " " + arrival_time, "%d/%m/%Y %H:%M") # Parsing arrival datetime
        return int((arrival_datetime - departure_datetime).total_seconds() / 60) # Calculating and returning the total duration in minutes


def dijkstra(start_node_name, goal_node_name, departure_date, departure_time, arrival_date, arrival_time, graph):
    """
    Dijkstra's algorithm to find the shortest path between two train stations.

    Args:
        start_node_name (str): Name of the departure train station.
        goal_node_name (str): Name of the arrival train station.
        departure_date (str): Departure date.
        departure_time (str): Departure time.
        arrival_date (str): Arrival date.
        arrival_time (str): Arrival time.
        graph (Neo4jGraph): Instance of the Neo4jGraph class.

    Returns:
        list: Found path as a list of nodes.
    """
    open_set = []  # Set of nodes to evaluate
    closed_set = set() # Set of nodes already evaluated

    
    start_node = Node(start_node_name, departure_date, departure_time, arrival_date, arrival_time, "")
    start_node.distance = 0
    open_set.append(start_node)  # Add the start node to the "open" set
    
    while open_set:
        current_node = min(open_set, key=lambda x: x.distance)  # Select the node with the smallest distance in the "open" set
        open_set.remove(current_node)
        
        if current_node.name == goal_node_name:  # If the current node is the destination node, finish
            path = []
            while current_node:
                path.append(current_node)
                current_node = current_node.parent
            return path[::-1]  # Return the found path in the correct order

        closed_set.add(current_node.name)  # Move the current node from the "open" set to the "closed" set
        for neighbor, neighbor_distance in graph.get_neighbors(current_node.name, current_node.departure_date, current_node.departure_time):

            if neighbor.name in closed_set:  # If the neighbor is already evaluated, ignore
                continue

            tentative_distance = current_node.distance + neighbor_distance # Calculate the tentative distance to reach the neighbor from the current node

            if tentative_distance < neighbor.distance:  # If the tentative distance is less than the previous distance
                neighbor.parent = current_node  # Update the parent node for the neighbor
                neighbor.distance = tentative_distance  # Update the distance for the neighbor
                if neighbor not in open_set:  # If the neighbor is not in the "open" set
                    open_set.append(neighbor)  # Add the neighbor to the "open" set
            else:
                # If the neighbor is already in the "open" set but the tentative distance is greater,
                # we need to update the distance and parent of the neighbor
                if neighbor in open_set:
                    existing_neighbor = open_set[open_set.index(neighbor)]
                    if tentative_distance < existing_neighbor.distance:
                        existing_neighbor.distance = tentative_distance
                        existing_neighbor.parent = current_node

    return None  # No path found


def get_user_input():
    """
    Asks the user to provide information about the desired journey.
    """
    mode_choice = input("Choisissez le mode (1: Tous les trajets possibles, 2: Trajet le plus direct, 3: Tour de France) : ").strip()
    while mode_choice not in ('1', '2','3'):
        mode_choice = input("Choisissez le mode (1: Trajet normal, 2: Tour de France) : ").strip()

    if mode_choice == '1':
            start_node_name = input("Entrez le nom de la gare de départ : ").strip().upper()
            goal_node_name = input("Entrez le nom de la gare d'arrivée : ").strip().upper()
            departure_date=input("Entrez la date de départ (format JJ/MM/AAAA) : ").strip()
            departure_time="00:00"
            return 'facile', start_node_name, goal_node_name, departure_date, departure_time
    
    elif mode_choice == '2':
        start_node_name = input("Entrez le nom de la gare de départ : ").strip().upper()
        goal_node_name = input("Entrez le nom de la gare d'arrivée : ").strip().upper()
        departure_date = input("Entrez la date de départ (format JJ/MM/AAAA) : ").strip()
        mode_choice2 = input("Choisissez le mode (1: Heure de départ ,2: Heure d'arriver) : ").strip()
        while mode_choice2 not in ('1', '2'):
            mode_choice2 = input("Choisissez le mode (1: Heure de départ ,2: Heure d'arriver) : ").strip()
        if mode_choice2=='1':
            departure_time = input("Entrez l'heure de départ (format HH:MM) : ").strip()
            arrival_time_mode="00:00"
            return 'normal', start_node_name, goal_node_name, departure_date, departure_time,arrival_time_mode,mode_choice2
        if mode_choice2=='2':
            departure_time ="00:00"
            arrival_time_mode = input("Entrez l'heure de d'arriver (format HH:MM) : ").strip()
            return 'normal', start_node_name, goal_node_name, departure_date, departure_time,arrival_time_mode,mode_choice2

    elif mode_choice == '3':
        mode_choice3 = input("Choisissez le mode (1: Choisir vos destinations et le nombres d'étapes que vous voulez, 2: Itinéraire préconçu) : ").strip()
        while mode_choice3 not in ('1', '2'):
            mode_choice3 = input("Choisissez le mode (1: Choisir vos destinations et le nombres d'étapes que vous voulez, 2: Itinéraire préconçu) : ").strip()
        if mode_choice3=='1':
            start_node_name = input("Entrez le nom de la gare de départ : ").strip().upper()
            nb_etape = input("Combien d'étapes souhaitez vous faire ?")
            intermediate_cities = []
            for i in range(int(nb_etape)):
                city = input(f"Entrez le nom de la ville intermédiaire {i+1} : ").strip().upper()
                intermediate_cities.append(city)
            start_date = input("Entrez la date de début du Tour de France (format JJ/MM/AAAA) : ").strip()
            
            return 'tour_de_france', start_node_name, intermediate_cities, start_date
        if mode_choice3=='2':
            print(f"Choisissez votre parcours: "  )
            print(f"- Itinéraire 1 Route du soleil en méditéranée: De Nice Ville à Barcelona Sants"  )
            print(f"- Itinéraire 2 Visite de l'Atlantique: De Biaritz à St Malo"  )
            print(f"- Itinéraire 3 Les plus grandent ville de france: De Nice Ville à Lyon Part Dieu en passant par Bordeaux, Rennes, Paris et Strasbourg"  )
            print(f"- Itinéraire 4 Entre lac et volcan: De Aurillac à Lausanne"  )
            print(f"- Itinéraire 5 Visite culturel Français des cathédrales aux chateaux: De Strasbourg à Angers"  )
            mode_choice4 = input("Lequel choisissez vous (1,2,3,4 ou 5): ").strip()
            while mode_choice4 not in ('1', '2','3','4','5'):
                mode_choice4 = input("Lequel choisissez vous (1,2,3,4 ou 5): ").strip()
            if mode_choice4=='1':
                departure_date1 = input("Entrez la date de départ de Nice Ville -> Marseille St Charles (format JJ/MM/AAAA) : ").strip()
                departure_time1 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date2 = input("Entrez la date de départ de Marseille St Charles -> Montpellier Saint-Roch (format JJ/MM/AAAA) : ").strip()
                departure_time2 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date3 = input("Entrez la date de départ de Montpellier Saint-Roch -> Agde  (format JJ/MM/AAAA) : ").strip()
                departure_time3 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date4 = input("Entrez la date de départ de Agde -> Barcelona Sants (format JJ/MM/AAAA) : ").strip()
                departure_time4 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                return 'tour_de_france1', departure_date1, departure_time1, departure_date2,departure_time2,departure_date3,departure_time3,departure_date4,departure_time4,mode_choice4
            elif mode_choice4=='2':
                departure_date1 = input("Entrez la date de départ de Biaritz -> Arcachon (format JJ/MM/AAAA) : ").strip()
                departure_time1 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date2 = input("Entrez la date de départ de Arcachon -> Sables d'Olonne (format JJ/MM/AAAA) : ").strip()
                departure_time2 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date3 = input("Entrez la date de départ de Sables d'Olonne -> St Nazaire  (format JJ/MM/AAAA) : ").strip()
                departure_time3 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date4 = input("Entrez la date de départ de St Nazaire -> St Malo (format JJ/MM/AAAA) : ").strip()
                departure_time4 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                return 'tour_de_france1', departure_date1, departure_time1, departure_date2,departure_time2,departure_date3,departure_time3,departure_date4,departure_time4,mode_choice4
            elif mode_choice4=='3':
                departure_date1 = input("Entrez la date de départ de Nice Ville -> Marseille St Charles (format JJ/MM/AAAA) : ").strip()
                departure_time1 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date2 = input("Entrez la date de départ de Marseille St Charles -> Bordeaux St Jean (format JJ/MM/AAAA) : ").strip()
                departure_time2 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date3 = input("Entrez la date de départ de Bordeaux St Jean -> Rennes  (format JJ/MM/AAAA) : ").strip()
                departure_time3 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date4 = input("Entrez la date de départ de Rennes -> Paris Montparnasse (format JJ/MM/AAAA) : ").strip()
                departure_time4 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date5 = input("Entrez la date de départ de Paris Montparnasse -> Strasbourg (format JJ/MM/AAAA) : ").strip()
                departure_time5 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date6 = input("Entrez la date de départ de Strasbourg -> Lyon Part Dieu (format JJ/MM/AAAA) : ").strip()
                departure_time6 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                return 'tour_de_france2', departure_date1, departure_time1, departure_date2,departure_time2,departure_date3,departure_time3,departure_date4,departure_time4,departure_date5,departure_time5,departure_date6,departure_time6,mode_choice4
            elif mode_choice4=='4':
                departure_date1 = input("Entrez la date de départ de Aurillac -> Clermont Ferrand (format JJ/MM/AAAA) : ").strip()
                departure_time1 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date2 = input("Entrez la date de départ de Clermont Ferrand -> Aix les Bains le Revard (format JJ/MM/AAAA) : ").strip()
                departure_time2 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date3 = input("Entrez la date de départ de Aix les Bains le Revard -> Annecy  (format JJ/MM/AAAA) : ").strip()
                departure_time3 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date4 = input("Entrez la date de départ de Annecy -> Lausanne (format JJ/MM/AAAA) : ").strip()
                departure_time4 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                return 'tour_de_france1', departure_date1, departure_time1, departure_date2,departure_time2,departure_date3,departure_time3,departure_date4,departure_time4,mode_choice4
            elif mode_choice4=='5':
                departure_date1 = input("Entrez la date de départ de Strasbourg -> Reims (format JJ/MM/AAAA) : ").strip()
                departure_time1 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date2 = input("Entrez la date de départ de Reims -> Versailles Chantiers (format JJ/MM/AAAA) : ").strip()
                departure_time2 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date3 = input("Entrez la date de départ de Versailles Chantiers -> Tours  (format JJ/MM/AAAA) : ").strip()
                departure_time3 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                departure_date4 = input("Entrez la date de départ de Tours -> Angers (format JJ/MM/AAAA) : ").strip()
                departure_time4 = input("Entrez l'heure de départ (format HH:MM) : ").strip()
                return 'tour_de_france1', departure_date1, departure_time1, departure_date2,departure_time2,departure_date3,departure_time3,departure_date4,departure_time4,mode_choice4

def main():
    # Neo4j database connection details
    uri = "bolt://3.226.239.114:7687"
    user = "neo4j"
    password = "valve-jam-regulations"
    
    # Get the user's mode choice and input information
    mode, *user_input = get_user_input()
    
    # Initialize the Neo4jGraph object
    graph = Neo4jGraph(uri, user, password)

    if mode == 'facile': # If the mode is 'easy'
        start_node_name, goal_node_name, departure_date, departure_time = user_input

        # Get information about the first nodes for each train departing from the start station
        premier_nodes = graph.get_premiernodes(start_node_name, departure_date, departure_time)

        if premier_nodes: # If there are premier nodes available
            for premier_node in premier_nodes:
                # Use Dijkstra's algorithm to find the path for each train
                path = dijkstra(start_node_name, goal_node_name, premier_node.departure_date, premier_node.departure_time, premier_node.arrival_date, premier_node.arrival_time, graph)
                if path:# If a path is found
                    # Get departure and arrival node information
                    departure_node = path[0]
                    arrival_node = path[-2]
                    print("Ville de départ:", departure_node.name)
                    print("Départ à", departure_node.departure_time, "du train", premier_node.train_number, "le", departure_node.departure_date)
                    print("Ville d'arrivée:", arrival_node.name)
                    print("Arrivée à", arrival_node.arrival_time, "le", arrival_node.arrival_date)

                    # Print journey details
                    print("Détail du trajet:")
                    
                    for i in range(0,len(path)):
                        current_node = path[i]
                        if i == (len(path)-1) : 
                            current_node2 = path[i-1]
                            print(f"- Nom de la gare : {current_node.name} Arrive à {current_node2.arrival_time} le {current_node2.arrival_date} "  ) ### MODIFIER
                        else :
                            print(f"- Nom de la gare : {current_node.name} Départ à {current_node.departure_time} le {current_node.departure_date} "  ) ### MODIFIER
                        
                else:
                    print(f"Aucun chemin trouvé pour le train {premier_node.train_number}")
        else:
            print("Aucun train trouvé au départ de la gare de départ")

    elif mode == 'normal': # If the mode is 'normal'
        start_node_name, goal_node_name, departure_date, departure_time,arrival_time_mode,mode_choice2 = user_input

       # Get information about the first nodes for each train departing from the start station
        premier_nodes = graph.get_premiernodes(start_node_name, departure_date, departure_time)
        if mode_choice2=="1": # If mode choice is 'Departure time'
            if premier_nodes: # If there are premier nodes available
                for premier_node in premier_nodes:
                    
                    # Use Dijkstra's algorithm to find the path for each train
                    path = dijkstra(start_node_name, goal_node_name, premier_node.departure_date, premier_node.departure_time, premier_node.arrival_date, premier_node.arrival_time, graph)
                    print(path)
                    if path: # If a path is found
                        # Get departure and arrival node information
                        departure_node = path[0]
                        arrival_node = path[-2]

                        # Print information
                        print("Ville de départ:", departure_node.name)
                        print("Départ à", departure_node.departure_time, "du train", premier_node.train_number, "le", departure_node.departure_date)
                        print("Ville d'arrivée:", arrival_node.name)
                        print("Arrivée à", arrival_node.arrival_time, "le", arrival_node.arrival_date)

                        # Calculate the expected time between departure and arrival
                        total_time = graph.calculate_total_time(departure_node.departure_date, departure_node.departure_time, arrival_node.arrival_date, arrival_node.arrival_time)
                        print("Temps prévu:", total_time, "minutes")

                        # Print journey detail
                        print("Détail du trajet:")
                        for i in range(0,len(path)-1):
                            current_node = path[i]
                            next_node = path[i+1]
                            print(f"- Nom de la gare : {current_node.name}")
                            print(f"  - Départ à {current_node.departure_time} du train {current_node.train_number} de {current_node.name}, arrive à {current_node.arrival_time} le {current_node.arrival_date} à {next_node.name}")

                    else:
                        print(f"Aucun chemin trouvé pour le train {premier_node.train_number}")
            else:
                print("Aucun train trouvé au départ de la gare de départ")

        elif mode_choice2=="2": # If mode choice is 'Arrival time'
            # Initialization
            Liste=[]
            L=[]
            if premier_nodes: # If there are premier nodes available
                for premier_node in premier_nodes:
                    # Use Dijkstra's algorithm to find the path for each train
                    path = dijkstra(start_node_name, goal_node_name, premier_node.departure_date, premier_node.departure_time, premier_node.arrival_date, premier_node.arrival_time, graph)
                    if path: # If a path is found
                        L2=[]
                        # Get departure and arrival node information
                        departure_node = path[0]
                        arrival_node = path[-2]
                        # Calculate the expected time between departure and arrival
                        temps=Neo4jGraph.calculate_total_time(departure_date, arrival_node.arrival_time, departure_date, arrival_time_mode)
                        path.append(temps)
                        L2.append(path)
                        Liste+=L2
                        L.append(int(temps))
                    else:
             
                        print(f"Aucun chemin trouvé pour le train {premier_node.train_number}")
            if L:
                print(Liste)
                smallest_positive=None
                # Iterate through the list
                for number in L:
                    # Check if the number is positive
                    if number > 0:
                        # If smallest_positive is None or the number is smaller than smallest_positive
                        if smallest_positive is None or number < smallest_positive:
                            smallest_positive = number

                # Iterate through the two-dimensional list
                for i, sous_liste in enumerate(Liste):
                    # Check if the desired value is present in the sublist
                    if smallest_positive in sous_liste:
                        index=i
                        # Stop the loop since we found the first occurrence
                        break
                
                min_path = Liste[index]
                print(smallest_positive,index,min_path)

                # Calculate the expected time between departure and arrival
                departure_node = min_path[0]
                arrival_node = min_path[-3]

                # Print journey detail
                print("Ville de départ:", departure_node.name)
                print("Départ à", departure_node.departure_time, "du train", premier_node.train_number, "le", departure_node.departure_date)
                print("Ville d'arrivée:", arrival_node.name)
                print("Arrivée à", arrival_node.arrival_time, "le", arrival_node.arrival_date)

                # Calculate the expected time between departure and arrival
                total_time = graph.calculate_total_time(departure_node.departure_date, departure_node.departure_time, arrival_node.arrival_date, arrival_node.arrival_time)
                print("Temps prévu:", total_time, "minutes")

                # Print journey detail
                print("Détail du trajet:")
                for i in range(0, len(min_path)-2):
                    current_node = min_path[i]
                    next_node = min_path[i+1]
                    print(f"- Nom de la gare : {current_node.name}")
                    print(f"  - Départ à {current_node.departure_time} du train {current_node.train_number} de {current_node.name}, arrive à {current_node.arrival_time} le {current_node.arrival_date} à {next_node.name}")
            else:
                print("Aucun train trouvé au départ de la gare de départ")

    elif mode == 'tour_de_france': # If the mode is 'tour_de_france'
        start_node_name, intermediate_cities, start_date = user_input

        # Initialize variables to store the departure and destination of each stage
        current_city = start_node_name
        current_date = start_date

        # Iterate through each stage of the Tour de France
        for i in range(len(intermediate_cities)):
            goal_city = intermediate_cities[i]

            # Get information about the first nodes for each train departing from the current city
            premier_nodes = graph.get_premiernodes(current_city, current_date, "00:00")

            if premier_nodes: # If there are premier nodes available
                # Use the first available trip for each stage
                premier_node = premier_nodes[0]
                # Use Dijkstra's algorithm to find the path for this train to the next city
                path = dijkstra(current_city, goal_city, premier_node.departure_date, premier_node.departure_time, premier_node.arrival_date, premier_node.arrival_time, graph)
                if path: # If a path is found
                    # Get departure and arrival node information
                    departure_node = path[0]
                    arrival_node = path[-2]

                    # Print information for each stage of the Tour de France
                    print(f"Étape {i+1}: {departure_node.name} -> {arrival_node.name}")
                    print("Départ à", departure_node.departure_time, "le", departure_node.departure_date)
                    print("Arrivée à", arrival_node.arrival_time, "le", arrival_node.arrival_date)

                    # Calculate the expected time between departure and arrival
                    total_time = graph.calculate_total_time(departure_node.departure_date, departure_node.departure_time, arrival_node.arrival_date, arrival_node.arrival_time)
                    print("Temps prévu:", total_time, "minutes")

                    # Print journey detail for each stage of the Tour de France
                    print("Détail du trajet:")
                    for i in range(0, len(path)-1):
                        current_node = path[i]
                        next_node = path[i+1]
                        print(f"- Nom de la gare : {current_node.name}")
                        print(f"  - Départ à {current_node.departure_time} du train {current_node.train_number} de {current_node.name}, arrive à {current_node.arrival_time} le {current_node.arrival_date} à {next_node.name}")

                    # Update the current city for the next stage
                    current_city = goal_city
                    current_date = (datetime.strptime(arrival_node.arrival_date, "%d/%m/%Y") + timedelta(days=1)).strftime("%d/%m/%Y")

                else:
                    print(f"Aucun chemin trouvé pour le train {premier_node.train_number} jusqu'à {goal_city}")
            else:
                print(f"Aucun train trouvé au départ de {current_city} pour aller à {goal_city}")
        
    elif mode == 'tour_de_france1': # If the mode is 'tour_de_france1'
        departure_date1, departure_time1, departure_date2,departure_time2,departure_date3,departure_time3,departure_date4,departure_time4,mode_choice4 = user_input
        if mode_choice4=='1':  # If mode choice is '1'
            # List of cities and departure dates and times for mode choice 1
            ListeVille1=[["NICE VILLE",departure_date1, departure_time1],["MARSEILLE ST CHARLES",departure_date2,departure_time2],["MONTPELLIER SAINT-ROCH",departure_date3,departure_time3],["AGDE",departure_date4,departure_time4],["BARCELONA SANTS"]]
        elif mode_choice4=='2': # If mode choice is '2'
            # List of cities and departure dates and times for mode choice 2
            ListeVille1=[["BIARITZ",departure_date1, departure_time1],["ARCACHON",departure_date2,departure_time2],["SABLES D'OLONNE",departure_date3,departure_time3],["ST NAZAIRE",departure_date4,departure_time4],["ST MALO"]]
        elif mode_choice4=='4': # If mode choice is '4'
            # List of cities and departure dates and times for mode choice 4
            ListeVille1=[["AURILLAC",departure_date1, departure_time1],["CLERMONT FERRAND",departure_date2,departure_time2],["AIX LES BAINS LE REVARD",departure_date3,departure_time3],["ANNECY",departure_date4,departure_time4],["LAUSANNE"]]
        elif mode_choice4=='5': # If mode choice is '5'
            # List of cities and departure dates and times for mode choice 5
            ListeVille1=[["STRASBOURG",departure_date1, departure_time1],["REIMS",departure_date2,departure_time2],["VERSAILLES CHANTIERS",departure_date3,departure_time3],["TOURS",departure_date4,departure_time4],["ANGERS"]]
        # re_tInitialize variables to store the departure and destination of each stage
        current_city = ListeVille1[0][0]
        current_date = ListeVille1[0][1]
        curent_time = ListeVille1[0][2]
        # Iterate through each stage
        for i in range(1,len(ListeVille1)):
            goal_city = ListeVille1[i][0]

            # Get information about the first nodes for each train departing from the current city
            premier_nodes = graph.get_premiernodes(current_city, current_date, curent_time)

            if premier_nodes: # If there are premier nodes available
                 # Use the first available trip for each stage
                premier_node = premier_nodes[0]
                # Use Dijkstra's algorithm to find the path for this train to the next city
                path = dijkstra(current_city, goal_city, premier_node.departure_date, premier_node.departure_time, premier_node.arrival_date, premier_node.arrival_time, graph)
                if path:# If a path is found
                    # Get departure and arrival node information
                    departure_node = path[0]
                    arrival_node = path[-1]

                    # Print information for each stage
                    print(f"Étape {i} : {departure_node.name} -> {arrival_node.name}")
                    print("Départ à", departure_node.departure_time, "le", departure_node.departure_date)
                    print("Arrivée à", arrival_node.arrival_time, "le", arrival_node.arrival_date)

                    # Calculate the expected time between departure and arrival
                    total_time = graph.calculate_total_time(departure_node.departure_date, departure_node.departure_time, arrival_node.arrival_date, arrival_node.arrival_time)
                    print("Temps prévu:", total_time, "minutes")

                    # Print journey detail for each stage
                    print("Détail du trajet:")
                    for j in range(0, len(path)-1):
                        current_node = path[j]
                        next_node = path[j+1]
                        print(f"- Nom de la gare : {current_node.name}")
                        print(f"  - Départ à {current_node.departure_time} du train {current_node.train_number} de {current_node.name}, arrive à {current_node.arrival_time} le {current_node.arrival_date} à {next_node.name}")

                    
                else:
                    print(f"Aucun chemin trouvé pour le train {premier_node.train_number} jusqu'à {goal_city}")
            else:
                print(f"Aucun train trouvé au départ de {current_city} pour aller à {goal_city}")
            if i==(len(ListeVille1)-1):
                break
            else:
                # Update the current city for the next stage
                current_city = goal_city
                current_date = ListeVille1[i][1]
                curent_time = ListeVille1[i][2]

    elif mode == 'tour_de_france2':
        # Extracting user input for departure dates, times, and mode choice
        departure_date1, departure_time1, departure_date2,departure_time2,departure_date3,departure_time3,departure_date4,departure_time4,departure_date5,departure_time5,departure_date6,departure_time6,mode_choice4 = user_input
        # List of cities and their corresponding departure dates and times
        ListeVille1=[["NICE VILLE",departure_date1, departure_time1],["MARSEILLE ST CHARLES",departure_date2,departure_time2],["BORDEAUX ST JEAN",departure_date3,departure_time3],["RENNES",departure_date4,departure_time4],["PARIS MONTPARNASSE",departure_date5,departure_time5],["STRASBOURG",departure_date6,departure_time6],["LYON PART DIEU"]]
        # Initialize variables to store the departure city, date, and time
        current_city = ListeVille1[0][0]
        current_date = ListeVille1[0][1]
        curent_time = ListeVille1[0][2]
        # Loop through each stage of the Tour de France
        for i in range(1,len(ListeVille1)):
            goal_city = ListeVille1[i][0]

            # Get the first nodes for each train departing from the current city
            premier_nodes = graph.get_premiernodes(current_city, current_date, curent_time)

            if premier_nodes:
                # Use the first available trip for each stage
                premier_node = premier_nodes[0]
                # Use Dijkstra's algorithm to find the path for this train to the next city
                path = dijkstra(current_city, goal_city, premier_node.departure_date, premier_node.departure_time, premier_node.arrival_date, premier_node.arrival_time, graph)
                if path:
                    # Get departure and arrival node information
                    departure_node = path[0]
                    arrival_node = path[-1]

                    # Print information for each stage of the Tour de France
                    print(f"Étape {i} : {departure_node.name} -> {arrival_node.name}")
                    print("Départ à", departure_node.departure_time, "le", departure_node.departure_date)
                    print("Arrivée à", arrival_node.arrival_time, "le", arrival_node.arrival_date)

                    # Calculate the expected time between departure and arrival
                    total_time = graph.calculate_total_time(departure_node.departure_date, departure_node.departure_time, arrival_node.arrival_date, arrival_node.arrival_time)
                    print("Temps prévu:", total_time, "minutes")

                    # Print journey detail for each stage of the Tour de France
                    print("Détail du trajet:")
                    for j in range(0, len(path)-1):
                        current_node = path[j]
                        next_node = path[j+1]
                        print(f"- Nom de la gare : {current_node.name}")
                        print(f"  - Départ à {current_node.departure_time} du train {current_node.train_number} de {current_node.name}, arrive à {current_node.arrival_time} le {current_node.arrival_date} à {next_node.name}")

                    
                else:
                    print(f"Aucun chemin trouvé pour le train {premier_node.train_number} jusqu'à {goal_city}")
            else:
                print(f"Aucun train trouvé au départ de {current_city} pour aller à {goal_city}")
            if i==(len(ListeVille1)-1):
                break
            else:
                # Update the current city for the next stage
                current_city = goal_city
                current_date = ListeVille1[i][1]
                curent_time = ListeVille1[i][2]

        graph.close()

# Execute the main function if the script is run directly
if __name__ == "__main__":
    main()
