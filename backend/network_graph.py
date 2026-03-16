from typing import List, Dict, Set, Any
from collections import defaultdict
from datetime import datetime


class Node:
    """Represents a node in the fraud network graph"""
    def __init__(self, upi_id: str, node_type: str = "normal"):
        self.id = upi_id
        self.type = node_type  # normal, suspicious, mule
        self.transaction_count = 0
        self.total_amount = 0.0
        self.senders: Set[str] = set()
        self.receivers: Set[str] = set()
        self.transactions: List[Dict] = []
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "transaction_count": self.transaction_count,
            "total_amount": self.total_amount
        }


class Edge:
    """Represents an edge (transaction) in the fraud network graph"""
    def __init__(self, source: str, target: str, amount: float, timestamp: str, transaction_id: str):
        self.source = source
        self.target = target
        self.amount = amount
        self.timestamp = timestamp
        self.transaction_id = transaction_id
    
    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "target": self.target,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "transaction_id": self.transaction_id
        }


class FraudNetworkGraph:
    """
    Graph data structure tracking accounts and transactions
    for fraud detection and network analysis.
    """
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
    
    def add_transaction_to_graph(self, sender_upi: str, receiver_upi: str, 
                                  amount: float, timestamp: str, transaction_id: str):
        """
        Add sender and receiver as nodes, and transaction as an edge.
        """
        # Create or update sender node
        if sender_upi not in self.nodes:
            self.nodes[sender_upi] = Node(sender_upi, "normal")
        
        sender_node = self.nodes[sender_upi]
        sender_node.transaction_count += 1
        sender_node.total_amount += amount
        sender_node.receivers.add(receiver_upi)
        
        # Create or update receiver node
        if receiver_upi not in self.nodes:
            self.nodes[receiver_upi] = Node(receiver_upi, "normal")
        
        receiver_node = self.nodes[receiver_upi]
        receiver_node.transaction_count += 1
        receiver_node.total_amount += amount
        receiver_node.senders.add(sender_upi)
        
        # Add edge
        edge = Edge(sender_upi, receiver_upi, amount, timestamp, transaction_id)
        self.edges.append(edge)
        
        # Update node types based on network behavior
        self._update_node_types()
    
    def _update_node_types(self):
        """Update node types based on network behavior"""
        for node_id, node in self.nodes.items():
            # Check for mule accounts (receiving from 3+ different senders)
            if len(node.senders) >= 3:
                node.type = "mule"
            # Check for suspicious accounts
            elif node.transaction_count > 20 or node.total_amount > 1000000:
                node.type = "suspicious"
    
    def detect_mule_accounts(self) -> List[Dict]:
        """
        Find accounts receiving money from 3+ different senders.
        These are potential money mule accounts.
        """
        mule_accounts = []
        
        for node_id, node in self.nodes.items():
            if len(node.senders) >= 3:
                mule_accounts.append({
                    "upi_id": node_id,
                    "type": "mule",
                    "different_senders": len(node.senders),
                    "transaction_count": node.transaction_count,
                    "total_amount": node.total_amount
                })
        
        return mule_accounts
    
    def get_fraud_network_data(self) -> Dict:
        """
        Return network graph data ready for D3.js visualization.
        """
        nodes = []
        edges = []
        
        # Get all nodes
        for node_id, node in self.nodes.items():
            nodes.append({
                "id": node.id,
                "type": node.type,
                "transaction_count": node.transaction_count,
                "total_amount": node.total_amount,
                # Color coding for visualization
                "color": self._get_node_color(node.type)
            })
        
        # Get all edges
        for edge in self.edges:
            edges.append({
                "source": edge.source,
                "target": edge.target,
                "amount": edge.amount,
                "timestamp": edge.timestamp,
                "transaction_id": edge.transaction_id
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "mule_accounts": self.detect_mule_accounts()
        }
    
    def _get_node_color(self, node_type: str) -> str:
        """Get color for node type"""
        colors = {
            "normal": "#00ff88",
            "suspicious": "#ffaa00",
            "mule": "#ff4444"
        }
        return colors.get(node_type, "#888888")
    
    def get_network_risk_score(self, upi_id: str) -> float:
        """
        Calculate network-based risk score for a given UPI ID.
        """
        if upi_id not in self.nodes:
            return 0.0
        
        node = self.nodes[upi_id]
        
        # Base score from node type
        type_scores = {"normal": 0, "suspicious": 30, "mule": 70}
        score = type_scores.get(node.type, 0)
        
        # Add score for number of unique senders (potential mule indicator)
        if len(node.senders) >= 3:
            score += min(len(node.senders) * 5, 25)
        
        return min(score, 100.0)


# Global instance
fraud_network = FraudNetworkGraph()
