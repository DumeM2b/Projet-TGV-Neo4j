Laura VERCHERE
Andrea MACHEDA
Liam HUISSOUD

# Projet-TGV-Neo4j

The goal of the project is to provide the user with the railway route to travel from a departure station A to a departure station B, both previously provided by the user. Additionally, refinement by departure or arrival time will also be possible.

Before indicating the route to the user, it is necessary to retrieve and store all the railway network data obtained from the SNCF website. Here, we focused on TGV INOUI and INTERCITÉS trains, which represent over 350,000 data entries.

An essential step before any data exploitation is Data Cleaning. Indeed, it is necessary to remove all unnecessary data to reduce the amount of data to be processed and thus improve the execution time of our program. Therefore, we removed data rows where:
  • The IATA code was DEEAA as some information was null.
  • The departure or arrival station name was TBD: an unrecognized station name, and it was about buses, not trains.
  • Duplicates. For example, in the initial database, we had trips A —> B, B—> C, and A —> C which corresponded to the same train. After processing, we only had the trip A —> B —> C left.

We also had to deal with night trains and manage the creation of an arrival date by setting it to the day after the train's departure date.

Data Cleaning allowed us to reduce the data from 350,000 entries to just under 100,000. Thus, we aimed to optimize our data as much as possible to efficiently process them later, significantly improving the execution time of our final algorithm. After analyzing and cleaning the database, we can define its schema:

![image](https://github.com/DumeM2b/Projet-TGV-No4j/assets/163656850/85147224-5070-43f5-b962-1f51c469d049)

This clarification and simplification of the database model allowed us to model it as a graph in neo4j:

![image](https://github.com/DumeM2b/Projet-TGV-No4j/assets/163656850/0ecae49a-f934-446d-b79d-ee0f39e193ee)

Here, the nodes represent stations, while the links correspond to trains between two stations.

Finally, the last step is to exploit this new database. We were asked to develop a programming code to achieve the following three points:
  • Display all trains allowing the journey between station A and station B on a specific date, all three provided by the user.
  • Display the direct route between station A and station B on a specific date, also provided by the user, who can also indicate either a departure or arrival time.
  • The itinerary for completing a Tour de France, for which the user must choose the number of stops and the cities they wish to visit.

To meet the functionalities above, we needed to design an algorithm to find the shortest path (here, the train) between a departure node (here, the departure station) and a destination node (here, the arrival station). We had two algorithm choices for this: A* or Dijkstra.
After implementing the A* algorithm on our database, we quickly realized that it was not the most optimal algorithm in our situation since it did not display the fastest route, quite the opposite. Despite significantly less execution speed than the A* algorithm, the Dijkstra algorithm allows us to display the shortest route. Therefore, we chose this algorithm.





