#!/usr/bin/env python3
"""Create a simplified, user-friendly view of the seed model."""

import json
from pathlib import Path

# Priority ranking for node types (higher = more important to show)
TYPE_PRIORITY = {
    'Reality': 10,
    'Subsystem': 9,
    'Module': 8,
    'Aspiration': 7,
    'Todo': 6,
    'Concept': 5,
    'Action': 4,
    'Change': 3,
    'Policy': 3,
    'Gap': 2,
    'Check': 2,
    'Audit': 1,
    'Proof': 1,
    'View': 1,
    'UIState': 0,
}

def load_sketch():
    """Load the current sketch.json."""
    with open('model/sketch.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_node_importance(node, edges):
    """Calculate importance score for a node."""
    node_type = node.get('type', 'unknown')
    type_score = TYPE_PRIORITY.get(node_type, 0) * 10

    # Count connections (edges involving this node)
    node_id = node.get('id')
    connection_count = sum(1 for e in edges if e.get('from') == node_id or e.get('to') == node_id)
    connection_score = min(connection_count * 2, 20)  # Cap at 20

    # Bonus for nodes with descriptions
    desc_score = 5 if node.get('description') else 0

    return type_score + connection_score + desc_score

def select_important_nodes(data, target_count=18):
    """Select the most important nodes to display."""
    nodes = data.get('nodes', [])
    edges = data.get('edges', [])

    # Calculate importance for each node
    node_scores = []
    for node in nodes:
        score = calculate_node_importance(node, edges)
        node_scores.append((score, node))

    # Sort by score and take top N
    node_scores.sort(reverse=True, key=lambda x: x[0])
    selected_nodes = [node for score, node in node_scores[:target_count]]

    return selected_nodes

def create_clean_layout(nodes):
    """Create a clean, centered layout with good spacing."""
    # Grid layout with generous spacing
    cols = 4
    rows = (len(nodes) + cols - 1) // cols

    # Spacing configuration
    horizontal_spacing = 350  # pixels between columns
    vertical_spacing = 200    # pixels between rows

    # Center the layout
    total_width = (cols - 1) * horizontal_spacing
    total_height = (rows - 1) * vertical_spacing
    start_x = -total_width / 2
    start_y = -total_height / 2

    # Assign positions
    for i, node in enumerate(nodes):
        row = i // cols
        col = i % cols

        x = start_x + col * horizontal_spacing
        y = start_y + row * vertical_spacing

        node['x'] = x
        node['y'] = y
        node['locked'] = True  # Lock positions

    return nodes

def filter_relevant_edges(nodes, all_edges):
    """Keep only edges that connect nodes in our simplified view."""
    node_ids = {node['id'] for node in nodes}
    return [
        edge for edge in all_edges
        if edge.get('from') in node_ids and edge.get('to') in node_ids
    ]

def create_simplified_view():
    """Main function to create simplified view."""
    print("Loading sketch.json...")
    data = load_sketch()

    print(f"Original: {len(data['nodes'])} nodes, {len(data['edges'])} edges")

    # Select important nodes
    print("Selecting most important nodes...")
    selected_nodes = select_important_nodes(data, target_count=18)

    print(f"Selected {len(selected_nodes)} nodes:")
    type_counts = {}
    for node in selected_nodes:
        node_type = node.get('type', 'unknown')
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
        print(f"  - {node.get('name', node.get('id'))} ({node_type})")

    print(f"\nNode type breakdown:")
    for node_type, count in sorted(type_counts.items()):
        print(f"  {node_type}: {count}")

    # Create clean layout
    print("\nCreating clean layout...")
    create_clean_layout(selected_nodes)

    # Filter edges
    filtered_edges = filter_relevant_edges(selected_nodes, data['edges'])
    print(f"Keeping {len(filtered_edges)} relevant edges")

    # Update data
    data['nodes'] = selected_nodes
    data['edges'] = filtered_edges
    data['description'] = "Simplified user-friendly view - 18 most important nodes"

    # Backup original
    backup_path = 'model/sketch.json.backup'
    print(f"\nCreating backup at {backup_path}...")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(load_sketch(), f, indent=2)

    # Write simplified version
    print("Writing simplified view to sketch.json...")
    with open('model/sketch.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print("\nSimplified view created successfully!")
    print(f"  Original backed up to: {backup_path}")
    print(f"  New view: {len(selected_nodes)} nodes, {len(filtered_edges)} edges")

if __name__ == '__main__':
    create_simplified_view()
