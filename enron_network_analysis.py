# ==============================================================================
#
# Enron Email Network Analysis
#
# This single script performs the following steps:
# 1.  Data Loading and Parsing: Reads the Enron email CSV and extracts a clean
#     'From' -> 'To' edge list.
# 2.  Graph Construction: Builds a weighted, directed graph using NetworkX.
# 3.  Analysis:
#     - Calculates In-Degree Centrality to measure influence.
#     - Performs Louvain Community Detection to find social clusters.
# 4.  Visualization: Creates and saves a plot of the core members of the
#     largest community, with node size representing influence.
#
# ==============================================================================

import os
import pandas as pd
import networkx as nx
import community as community_louvain
import matplotlib 
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from email.parser import Parser

# --- Configuration ---
# Path to the Kaggle CSV file
INPUT_CSV_PATH = 'data/emails.csv'

# File to save the cleaned edge list to 
CLEANED_DATA_PATH = 'enron_email_data.csv'

# Number of nodes to include in the final visualization
NUM_NODES_TO_VISUALIZE = 150

# Number of top nodes to label in the visualization
NUM_NODES_TO_LABEL = 15

# Output file for the final graph visualization
OUTPUT_IMAGE_FILE = 'enron_network_visualization.png'


def parse_emails_from_csv(input_csv, output_csv):
    """
    Step 1: Loads the Kaggle CSV, parses the raw email 'message' column,
    and saves a clean 'From', 'To' edge list.
    """
    print("--- Step 1: Loading and Parsing Raw Email Data ---")
    if os.path.exists(output_csv):
        print(f"Cleaned data file found at '{output_csv}'. Skipping parsing.")
        return pd.read_csv(output_csv)

    print(f"Loading raw data from '{input_csv}'...")
    df_raw = pd.read_csv(input_csv)

    def extract_email_info(message):
        try:
            email = Parser().parsestr(message)
            sender = email.get('From')
            recipients_to = email.get('To', '')
            recipients_cc = email.get('Cc', '')
            recipients_bcc = email.get('Bcc', '')
            all_recipients_str = f"{recipients_to}, {recipients_cc}, {recipients_bcc}"
            recipients = [r.strip() for r in all_recipients_str.split(',') if r.strip()]
            if sender and recipients:
                return sender, recipients
        except Exception:
            return None, []
        return None, []

    print("Parsing email messages... This may take a few minutes.")
    parsed_emails = df_raw['message'].apply(extract_email_info)

    edges = []
    for sender, recipients in parsed_emails:
        if sender and recipients:
            for recipient in recipients:
                edges.append({'From': sender, 'To': recipient})

    df_emails = pd.DataFrame(edges)
    print(f"Successfully parsed {len(df_emails)} email connections.")

    # Save the cleaned data to avoid re-parsing in the future
    df_emails.to_csv(output_csv, index=False)
    print(f"Cleaned data saved to '{output_csv}'.")
    return df_emails


def build_network_graph(df):
    """
    Step 2: Builds a weighted, directed graph from the email DataFrame.
    """
    print("\n--- Step 2: Building the Network Graph ---")
    # Clean up data
    df = df.dropna(subset=['From', 'To'])
    df = df[df['From'] != df['To']]  # Remove self-loops
    df['From'] = df['From'].str.strip()
    df['To'] = df['To'].str.strip()

    # Calculate edge weights
    weighted_edges = df.groupby(['From', 'To']).size().reset_index(name='weight')

    # Create the graph
    G = nx.from_pandas_edgelist(
        weighted_edges,
        source='From',
        target='To',
        edge_attr='weight',
        create_using=nx.DiGraph()
    )
    print(f"Graph built successfully.")
    print(f"  - Nodes (people): {G.number_of_nodes()}")
    print(f"  - Edges (connections): {G.number_of_edges()}")
    return G


def analyze_network(G):
    """
    Step 3 & 4: Calculates centrality and detects communities.
    """
    print("\n--- Step 3 & 4: Analyzing the Network ---")
    # Centrality Calculation
    print("Calculating In-Degree Centrality...")
    in_degree_centrality = nx.in_degree_centrality(G)

    # Community Detection
    print("Running Louvain Community Detection...")
    # Algorithm requires an undirected graph
    U = G.to_undirected()
    partition = community_louvain.best_partition(U, weight='weight')
    print(f"Found {len(set(partition.values()))} communities.")

    return in_degree_centrality, partition


def visualize_network(G, centrality, partition):
    """
    Step 5: Visualizes the core of the largest community.
    """
    print("\n--- Step 5: Creating Network Visualization ---")
    
    community_df = pd.DataFrame(partition.items(), columns=['Node', 'Community_ID'])
    largest_community_id = community_df['Community_ID'].value_counts().idxmax()
    largest_community_nodes = [
        node for node, comm_id in partition.items() if comm_id == largest_community_id
    ]

    community_centrality = {node: centrality[node] for node in largest_community_nodes}
    top_nodes = sorted(
        community_centrality, key=community_centrality.get, reverse=True
    )[:NUM_NODES_TO_VISUALIZE]
    
    S = G.subgraph(top_nodes)
    print(f"Visualizing the core network of {S.number_of_nodes()} nodes from the largest community.")

    node_sizes = [centrality[node] * 20000 for node in S.nodes()]
    pos = nx.spring_layout(S, k=0.6, iterations=50, seed=42)

    labels = {}
    for i, node in enumerate(S.nodes()):
        if i < NUM_NODES_TO_LABEL:
            labels[node] = node.split('@')[0].replace('.', ' ').title()

    plt.figure(figsize=(20, 20))
    nx.draw_networkx_edges(S, pos, alpha=0.05, width=0.5, edge_color="grey")
    nx.draw_networkx_nodes(S, pos, node_size=node_sizes, node_color="#1f78b4", alpha=0.8)
    nx.draw_networkx_labels(S, pos, labels=labels, font_size=12, font_weight="bold")

    plt.title("Core Network of Enron's Largest Communication Community", fontsize=24)
    plt.axis('off')

    plt.savefig(OUTPUT_IMAGE_FILE, dpi=300, bbox_inches='tight')
    print(f"\nVisualization saved to '{OUTPUT_IMAGE_FILE}'")


# --- Main Execution Flow ---
if __name__ == "__main__":
    if not os.path.exists(INPUT_CSV_PATH):
        print(f"Error: Input data file not found at '{INPUT_CSV_PATH}'")
        print("Please download the Kaggle 'emails.csv' and place it in the 'data' subfolder.")
    else:
        # Step 1
        email_df = parse_emails_from_csv(INPUT_CSV_PATH, CLEANED_DATA_PATH)
        
        # Step 2
        graph = build_network_graph(email_df)
        
        # Steps 3 & 4
        centrality, community_partition = analyze_network(graph)
        
        # Step 5
        visualize_network(graph, centrality, community_partition)
        
        print("\nProject finished successfully.")