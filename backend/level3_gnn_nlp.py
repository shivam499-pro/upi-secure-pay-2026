"""
Level 3 GNN + NLP Fraud Analyzer
Analyzes fraud network patterns and merchant NLP for advanced fraud detection.
"""

import networkx as nx
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import re


# ==================== PART A: Graph Neural Network (GNN) ====================

class TransactionGraph:
    """Transaction network graph using NetworkX"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.transaction_history = []  # List of (sender, receiver, amount, timestamp)
    
    def add_transaction(self, sender: str, receiver: str, amount: float, timestamp: str = None):
        """Add a transaction to the graph"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # Add or update nodes
        for node in [sender, receiver]:
            if node not in self.graph:
                self.graph.add_node(node, 
                    total_received=0, 
                    total_sent=0,
                    transaction_count=0,
                    unique_senders=set(),
                    unique_receivers=set(),
                    avg_amount=0,
                    is_in_blacklist=False,
                    account_age_days=0
                )
        
        # Add edge
        if self.graph.has_edge(sender, receiver):
            self.graph[sender][receiver]['count'] += 1
            self.graph[sender][receiver]['total_amount'] += amount
        else:
            self.graph.add_edge(sender, receiver, count=1, total_amount=amount)
        
        # Update node attributes
        self.graph.nodes[receiver]['total_received'] += amount
        self.graph.nodes[receiver]['transaction_count'] += 1
        self.graph.nodes[receiver]['unique_senders'].add(sender)
        
        self.graph.nodes[sender]['total_sent'] += amount
        self.graph.nodes[sender]['transaction_count'] += 1
        self.graph.nodes[sender]['unique_receivers'].add(receiver)
        
        # Store transaction for rapid forwarding detection
        self.transaction_history.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
            'timestamp': timestamp
        })
    
    def get_graph(self) -> nx.DiGraph:
        return self.graph


# Global transaction graph
transaction_graph = TransactionGraph()


def build_transaction_graph() -> nx.DiGraph:
    """
    Build account relationship graph using NetworkX.
    """
    return transaction_graph.get_graph()


def calculate_gnn_features(graph: nx.DiGraph, account_id: str) -> Dict:
    """
    Calculate graph-based features for an account.
    """
    features = {
        'in_degree': 0,
        'out_degree': 0,
        'clustering_coefficient': 0.0,
        'pagerank_score': 0.0,
        'betweenness': 0.0,
        'is_hub': False,
        'rapid_forwarding': False,
        'fan_in_pattern': False
    }
    
    if account_id not in graph:
        return features
    
    # Degree features
    features['in_degree'] = graph.in_degree(account_id)
    features['out_degree'] = graph.out_degree(account_id)
    
    # Is hub (potential mule account)
    features['is_hub'] = features['in_degree'] > 5
    
    # Clustering coefficient (for undirected version)
    undirected = graph.to_undirected()
    if account_id in undirected:
        features['clustering_coefficient'] = nx.clustering(undirected, account_id)
    
    # PageRank
    try:
        features['pagerank_score'] = nx.pagerank(graph).get(account_id, 0)
    except:
        features['pagerank_score'] = 0
    
    # Betweenness centrality
    try:
        features['betweenness'] = nx.betweenness_centrality(graph).get(account_id, 0)
    except:
        features['betweenness'] = 0
    
    # Rapid forwarding detection
    # Check if this account sends money within 60 seconds of receiving
    account_received = [t for t in transaction_graph.transaction_history 
                        if t['receiver'] == account_id]
    account_sent = [t for t in transaction_graph.transaction_history 
                    if t['sender'] == account_id]
    
    for recv_txn in account_received:
        recv_time = datetime.fromisoformat(recv_txn['timestamp'])
        for send_txn in account_sent:
            send_time = datetime.fromisoformat(send_txn['timestamp'])
            if send_time > recv_time:
                delta = (send_time - recv_time).total_seconds()
                if delta < 60:  # Less than 60 seconds
                    features['rapid_forwarding'] = True
                    break
    
    # Fan-in pattern (receives from 3+ different senders)
    features['fan_in_pattern'] = features['in_degree'] >= 3
    
    return features


def detect_fraud_patterns_gnn(graph: nx.DiGraph, account_id: str) -> Tuple[float, str, str]:
    """
    Detect specific fraud patterns using GNN analysis.
    
    Returns: (gnn_score, pattern_detected, reason)
    """
    features = calculate_gnn_features(graph, account_id)
    
    # MULE PATTERN: high in-degree, low out-degree
    if features['in_degree'] > 3 and features['out_degree'] < 2:
        return 0.9, "mule_pattern", "Mule account pattern detected"
    
    # RAPID FORWARDING
    if features['rapid_forwarding']:
        return 0.85, "rapid_forwarding", "Rapid money forwarding detected"
    
    # FAN-IN PATTERN
    if features['in_degree'] >= 5:
        return 0.8, "fan_in_pattern", "Fan-in fraud ring pattern detected"
    
    # CHAIN PATTERN: Check for A->B->C->D within 5 minutes
    try:
        if nx.has_path(graph, account_id, None):
            # Simplified chain detection
            successors = list(nx.descendants(graph, account_id))
            if len(successors) >= 3:
                return 0.75, "chain_pattern", "Transaction chain fraud detected"
    except:
        pass
    
    # HIGH RISK HUB
    if features['pagerank_score'] > 0.1 and features['is_hub']:
        return 0.7, "high_risk_hub", "High-risk network hub detected"
    
    return 0.0, "none", ""


# ==================== PART B: NLP Merchant Analyzer ====================

FRAUD_PATTERNS = {
    "lottery_scam": {
        "keywords": ["lucky draw", "lottery", "winner", "prize",
                     "KBC", "jackpot", "lucky winner", "cash prize"],
        "score": 0.95,
        "reason": "Lottery/prize scam language detected"
    },
    "bank_impersonation": {
        "keywords": ["bank helpdesk", "refund", "kyc update",
                     "account block", "verify account", "bank official",
                     "sbi help", "hdfc support", "axis care"],
        "score": 0.92,
        "reason": "Bank impersonation fraud pattern detected"
    },
    "advance_fee": {
        "keywords": ["processing fee", "refund fee", "registration fee",
                     "activation fee", "delivery charge", "customs fee"],
        "score": 0.90,
        "reason": "Advance fee fraud pattern pattern detected"
    },
    "government_impersonation": {
        "keywords": ["income tax", "it refund", "gst refund",
                     "pm relief", "government scheme", "aadhaar"],
        "score": 0.88,
        "reason": "Government impersonation fraud detected"
    },
    "investment_scam": {
        "keywords": ["high return", "guaranteed profit", "double money",
                     "investment plan", "crypto profit", "trading profit"],
        "score": 0.85,
        "reason": "Investment scam language detected"
    },
    "fake_merchant": {
        "keywords": ["unknown", "test", "temp", "demo123",
                     "random", "xyz services"],
        "score": 0.6,
        "reason": "Suspicious merchant name pattern"
    }
}

# Suspicious UPI ID patterns
SUSPICIOUS_UPI_PATTERNS = [
    r'\d{4,}',  # 4+ consecutive digits
    r'refund\d+',  # refund followed by numbers
    r'help\d+',  # help followed by numbers
    r'winner\d+',  # winner followed by numbers
    r'prize\d+',  # prize followed by numbers
]

# Known brand impersonation
BRAND_IMPERSONATION = ['sbi', 'hdfc', 'icici', 'axis', 'npci', 'paytm', 'phonepe', 'gpay', 'upi']


def analyze_merchant_nlp(merchant_name: str, upi_id: str) -> Tuple[float, str]:
    """
    Analyze merchant name and UPI ID using NLP.
    
    Returns: (nlp_score, reason)
    """
    merchant_lower = merchant_name.lower() if merchant_name else ""
    upi_lower = upi_id.lower() if upi_id else ""
    
    best_score = 0.1  # Default: appears legitimate
    best_reason = "Merchant appears legitimate"
    
    # Check merchant name against fraud patterns
    for pattern_name, pattern_data in FRAUD_PATTERNS.items():
        for keyword in pattern_data['keywords']:
            if keyword in merchant_lower:
                if pattern_data['score'] > best_score:
                    best_score = pattern_data['score']
                    best_reason = pattern_data['reason']
    
    # Check UPI ID against fraud patterns
    for pattern_name, pattern_data in FRAUD_PATTERNS.items():
        for keyword in pattern_data['keywords']:
            if keyword in upi_lower:
                if pattern_data['score'] > best_score:
                    best_score = pattern_data['score']
                    best_reason = pattern_data['reason']
    
    # Check for suspicious UPI ID patterns
    for pattern in SUSPICIOUS_UPI_PATTERNS:
        if re.search(pattern, upi_lower):
            if 0.7 > best_score:  # Don't override higher scores
                best_score = 0.7
                best_reason = "Suspicious UPI ID pattern detected"
    
    # Check for brand impersonation
    for brand in BRAND_IMPERSONATION:
        if brand in upi_lower and brand not in merchant_lower:
            # Brand in UPI but not in merchant name - potential impersonation
            if 0.8 > best_score:
                best_score = 0.8
                best_reason = f"Possible {brand} brand impersonation in UPI ID"
    
    return best_score, best_reason


# ==================== PART C: Integration ====================

def predict_level3_risk(
    merchant_name: str, 
    upi_id: str, 
    account_id: str,
    transaction_graph_data: nx.DiGraph = None
) -> Tuple[float, List[str], float, float, str]:
    """
    Combined GNN + NLP analysis for Level 3 risk assessment.
    
    Returns: (level3_score, reasons_list, gnn_score, nlp_score, level3_name)
    """
    # Get the graph
    if transaction_graph_data is None:
        transaction_graph_data = build_transaction_graph()
    
    # GNN Analysis
    gnn_score, gnn_pattern, gnn_reason = detect_fraud_patterns_gnn(transaction_graph_data, account_id)
    
    # NLP Analysis  
    nlp_score, nlp_reason = analyze_merchant_nlp(merchant_name, upi_id)
    
    # Combine scores
    if gnn_score > 0.5 and nlp_score > 0.5:
        level3_score = (gnn_score + nlp_score) / 2
    else:
        level3_score = max(gnn_score, nlp_score)
    
    # Collect reasons
    reasons = []
    if gnn_score > 0.5 and gnn_reason:
        reasons.append(gnn_reason)
    if nlp_score > 0.5 and nlp_reason:
        reasons.append(nlp_reason)
    
    return level3_score, reasons, gnn_score, nlp_score, "level3_gnn_nlp"


def initialize_level3():
    """
    Initialize Level 3 GNN+NLP system.
    """
    global transaction_graph
    
    # Add some sample fraud patterns to the graph for testing
    # This simulates known fraudulent networks
    sample_fraud_network = [
        ("fraud1@upi", "mule1@upi", 5000),
        ("fraud2@upi", "mule1@upi", 7000),
        ("fraud3@upi", "mule1@upi", 3000),
        ("fraud4@upi", "mule1@upi", 8000),
        ("mule1@upi", "boss@upi", 23000),  # Rapid forwarding
    ]
    
    for sender, receiver, amount in sample_fraud_network:
        transaction_graph.add_transaction(
            sender, receiver, amount,
            datetime.now().isoformat()
        )
    
    print("=" * 50)
    print("Level 3 GNN+NLP Initialized")
    print(f"Graph nodes: {transaction_graph.graph.number_of_nodes()}")
    print(f"Graph edges: {transaction_graph.graph.number_of_edges()}")
    print("=" * 50)
    
    return transaction_graph


def add_transaction_to_graph(sender: str, receiver: str, amount: float, timestamp: str = None):
    """Add a transaction to the Level 3 graph"""
    transaction_graph.add_transaction(sender, receiver, amount, timestamp)


# Test function
if __name__ == "__main__":
    initialize_level3()
    
    # Test with sample merchant
    score, reasons, gnn, nlp, name = predict_level3_risk(
        'Lucky Draw Services',
        'luckydraw@upi',
        'luckydraw@upi',
        None
    )
    
    print("\n--- Level 3 Test Results ---")
    print(f"Level 3 Score: {score}")
    print(f"GNN Score: {gnn}")
    print(f"NLP Score: {nlp}")
    print(f"Reasons: {reasons}")
    print(f"Level Name: {name}")
