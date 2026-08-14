"""
Quiz question bank for the Adaptive Quiz Engine.
Seeded with representative MCQs across AWS, Docker, and Kubernetes, at three
difficulty tiers per topic (mirrors the original 200-question bank structure,
just a smaller demo-sized set).
"""

QUESTION_BANK = {
    "AWS VPC": {
        "Easy": [
            {"q": "What does VPC stand for?",
             "options": ["Virtual Private Cloud", "Virtual Public Cloud", "Verified Private Connection", "Virtual Path Configuration"],
             "answer": 0},
            {"q": "Which AWS component allows a public subnet to reach the internet?",
             "options": ["NAT Gateway", "Internet Gateway", "VPN Gateway", "Transit Gateway"],
             "answer": 1},
            {"q": "A private subnet has a direct route to the internet by default.",
             "options": ["True", "False"], "answer": 1},
        ],
        "Medium": [
            {"q": "What does a NAT Gateway allow a private subnet resource to do?",
             "options": ["Accept inbound connections from the internet", "Initiate outbound connections to the internet only",
                         "Host a public website", "Bypass all security groups"],
             "answer": 1},
            {"q": "In a 3-tier VPC architecture, where would you place an RDS database?",
             "options": ["Public subnet", "Private application subnet", "Private database subnet", "Directly on the Internet Gateway"],
             "answer": 2},
        ],
        "Hard": [
            {"q": "A NAT Gateway must be deployed in which type of subnet?",
             "options": ["Private subnet", "Public subnet", "Either, it doesn't matter", "A dedicated NAT-only VPC"],
             "answer": 1},
            {"q": "Why is tiered subnet isolation (public/app/db) considered a security best practice?",
             "options": ["It reduces AWS billing", "It limits blast radius if one tier is compromised",
                         "It's required by AWS by default", "It increases internet speed"],
             "answer": 1},
        ],
    },
    "Docker Networking": {
        "Easy": [
            {"q": "What is the default Docker network called?",
             "options": ["host", "bridge", "overlay", "none"], "answer": 1},
            {"q": "Which flag maps a host port to a container port?",
             "options": ["-v", "-e", "-p", "-n"], "answer": 2},
        ],
        "Medium": [
            {"q": "What's an advantage of a user-defined bridge network over the default bridge?",
             "options": ["Faster internet speed", "Automatic DNS resolution by container name",
                         "Unlimited containers", "No firewall needed"],
             "answer": 1},
            {"q": "A container can't reach the internet. What's a likely first diagnostic command?",
             "options": ["docker ps", "docker network inspect", "docker images", "docker login"],
             "answer": 1},
        ],
        "Hard": [
            {"q": "Overlapping subnet ranges between Docker's bridge and the host network typically cause:",
             "options": ["Faster builds", "Routing conflicts", "Higher image size", "Better security"],
             "answer": 1},
            {"q": "Which host-level setting must be enabled for containers to forward traffic to the internet?",
             "options": ["net.ipv4.ip_forward", "docker.socket", "fs.inotify.max_user_watches", "vm.swappiness"],
             "answer": 0},
        ],
    },
    "Kubernetes": {
        "Easy": [
            {"q": "What is the smallest deployable unit in Kubernetes?",
             "options": ["Node", "Pod", "Cluster", "Container"], "answer": 1},
            {"q": "Which object manages a set of identical Pods?",
             "options": ["Deployment", "ConfigMap", "Secret", "Ingress"], "answer": 0},
        ],
        "Medium": [
            {"q": "Which Service type exposes Pods only within the cluster?",
             "options": ["NodePort", "LoadBalancer", "ClusterIP", "ExternalName"], "answer": 2},
            {"q": "What's the difference between a ConfigMap and a Secret?",
             "options": ["No difference", "Secrets are for sensitive data, base64-encoded",
                         "ConfigMaps are encrypted, Secrets are not", "Secrets can't be mounted as files"],
             "answer": 1},
        ],
        "Hard": [
            {"q": "What does the Horizontal Pod Autoscaler primarily react to by default?",
             "options": ["Disk I/O", "CPU utilization", "Network latency", "Pod age"], "answer": 1},
            {"q": "Why are Kubernetes Secrets not fully secure by default?",
             "options": ["They're stored in plaintext", "They're only base64-encoded, not encrypted, without extra config",
                         "They expire every hour", "They can't be used in Pods"],
             "answer": 1},
        ],
    },
}

DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]


def get_next_difficulty(recent_results, current_difficulty):
    """
    Adaptive logic mirroring the original design:
    - 3 consecutive correct at current level -> promote difficulty
    - Below 50% recent accuracy -> demote difficulty
    - Otherwise stay at current level
    """
    if len(recent_results) >= 3 and all(recent_results[:3]):
        idx = DIFFICULTY_ORDER.index(current_difficulty)
        return DIFFICULTY_ORDER[min(idx + 1, len(DIFFICULTY_ORDER) - 1)]

    if len(recent_results) >= 2:
        accuracy = sum(recent_results) / len(recent_results)
        if accuracy < 0.5:
            idx = DIFFICULTY_ORDER.index(current_difficulty)
            return DIFFICULTY_ORDER[max(idx - 1, 0)]

    return current_difficulty


def get_hint(topic, difficulty):
    hints = {
        "AWS VPC": "Think about which subnet has a route to the Internet Gateway.",
        "Docker Networking": "Think about which network Docker containers join by default.",
        "Kubernetes": "Think about what Kubernetes object type is being described.",
    }
    return hints.get(topic, "Review the course module for this topic.")
