import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

## Hard Filtering for Necessary Features

user = {
    "uid": "u1",
    "gender": 1,                     # 1=male, 2=female, 3=nonbinary
    "gender_pref": {"same", "opposite"},
    "housing": {"offcampus", "apartment"},
    "roommates": {1, 2},
    "has_pet": 1,                    # 1=yes, 2=no
    "pet_ok": 1                      # 1=yes, 2=no
}

def gender_blocks(u):
    blocks = set()

    if "same" in u["gender_pref"]:
        if u["gender"] == 1:
            blocks.add("M")   # male–male
        elif u["gender"] == 2:
            blocks.add("F")   # female–female

    if "opposite" in u["gender_pref"]:
        blocks.add("C")       # cross-gender

    return blocks

def pet_blocks(u):
    blocks = set()

    if u["has_pet"] == 1:
        blocks.add("P")   # pet owners
    else:
        blocks.add("N")   # no pets

    if u["pet_ok"] == 1:
        blocks.add("A")   # allows pets

    return blocks

def compute_blocks(u):
    keys = []

    for h in u["housing"]:
        for r in u["roommates"]:
            for g in gender_blocks(u):
                for p in pet_blocks(u):
                    keys.append((h, r, g, p))

    return keys

from collections import defaultdict

def build_blocks(users):
    blocks = defaultdict(set)

    for u in users:
        for key in compute_blocks(u):
            blocks[key].add(u["uid"])

    return blocks



## Clustering for Non Hard Filters

user["soft"] = [
    1,   # cleans immediately
    3,   # guests anytime
    2,   # alcohol sometimes
    1,   # quiet hours strict
    1,   # calm conflict
    1,   # don't take food
    2,   # 15–30 min commute
    3,   # $1200–1500
    6    # semesters
]


from sklearn.cluster import KMeans
import numpy as np

def cluster_block(block_users, user_map, k):
    X = []
    ids = []

    for uid in block_users:
        X.append(user_map[uid]["soft"])
        ids.append(uid)

    X = np.array(X)

    k = min(k, len(X))  # can't have more clusters than people
    model = KMeans(n_clusters=k, n_init=10)
    labels = model.fit_predict(X)

    clusters = {}
    for i, label in enumerate(labels):
        clusters.setdefault(label, []).append(ids[i])

    return clusters

def cluster_all_blocks(blocks, users, k=3):
    user_map = {u["uid"]: u for u in users}
    all_clusters = {}

    for block_key, members in blocks.items():
        if len(members) < 2:
            continue  # can't cluster 1 person

        clusters = cluster_block(members, user_map, k)
        all_clusters[block_key] = clusters

    return all_clusters



## Decision Tree (can be added later?)

# def pair_features(a, b):
#     return [
#         abs(a["clean"] - b["clean"]),
#         abs(a["noise"] - b["noise"]),
#         abs(a["guest"] - b["guest"]),
#         abs(a["alcohol"] - b["alcohol"]),
#         abs(a["budget"] - b["budget"]),
#         abs(a["commute"] - b["commute"]),
#         a["stay"] == b["stay"]
#     ]

# from sklearn.tree import DecisionTreeClassifier

# X = []   # pair features
# y = []   # 1 = compatible, 0 = not

# for (u, v, label) in training_pairs:
#     X.append(pair_features(u, v))
#     y.append(label)

# tree = DecisionTreeClassifier(
#     max_depth=6,
#     min_samples_leaf=20
# )
# tree.fit(X, y)

# def score_candidates(user, candidates, user_map, tree):
#     scores = []

#     for cid in candidates:
#         other = user_map[cid]
#         feats = pair_features(user, other)
#         prob = tree.predict_proba([feats])[0][1]
#         scores.append((cid, prob))

#     return sorted(scores, key=lambda x: -x[1])

import random
import numpy as np

def generate_user(uid):
    gender = np.random.choice([1,2,3], p=[0.48, 0.48, 0.04])
    
    if gender == 3:
        gender_pref = {"same", "opposite"}
    else:
        gender_pref = set(np.random.choice(
            ["same", "opposite", "both"], 
            p=[0.35, 0.35, 0.30]
        ).replace("both","same,opposite").split(","))

    housing = set(np.random.choice(
        ["offcampus", "apartment", "dorm"], 
        size=np.random.choice([1,2], p=[0.7,0.3]),
        replace=False
    ))

    roommates = set(np.random.choice([1,2,3,4], size=2, replace=False))
    has_pet = np.random.choice([1,2], p=[0.35, 0.65])
    pet_ok = np.random.choice([1,2], p=[0.75, 0.25])

    # --- correlated soft traits ---
    clean = np.random.choice([1,2,3], p=[0.4,0.4,0.2])
    guests = np.random.choice([1,2,3], p=[0.3,0.4,0.3])
    alcohol = np.random.choice([1,2,3], p=[0.35,0.45,0.2])
    quiet = 1 if clean == 1 else np.random.choice([1,2,3])
    conflict = np.random.choice([1,2,3], p=[0.6,0.3,0.1])
    food = np.random.choice([1,2], p=[0.7,0.3])

    commute = np.random.choice([1,2,3])
    budget = np.random.choice([1,2,3,4], p=[0.25,0.4,0.25,0.1])
    lease = np.random.choice([3,6,12], p=[0.2,0.5,0.3])

    return {
        "uid": f"u{uid}",
        "gender": gender,
        "gender_pref": gender_pref,
        "housing": housing,
        "roommates": roommates,
        "has_pet": has_pet,
        "pet_ok": pet_ok,
        "soft": [
            clean, guests, alcohol, quiet,
            conflict, food, commute,
            budget, lease
        ]
    }



users = [generate_user(i) for i in range(1000)]

blocks = build_blocks(users)
clusters = cluster_all_blocks(blocks, users, k=4)

from collections import Counter

print("Total users:", len(users))
print("Total blocks:", len(blocks))

block_sizes = [len(v) for v in blocks.values()]
print("Block size percentiles:", np.percentile(block_sizes, [10,25,50,75,90]))

appearance = Counter()
for b in blocks.values():
    for u in b:
        appearance[u] += 1

print("Avg blocks per user:", np.mean(list(appearance.values())))

cluster_sizes = []
for b in clusters.values():
    for c in b.values():
        cluster_sizes.append(len(c))

print("Cluster size percentiles:", np.percentile(cluster_sizes, [10,25,50,75,90]))