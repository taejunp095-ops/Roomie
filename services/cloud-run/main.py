import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from flask import Flask, request, jsonify
from google.cloud import firestore
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)
db = firestore.Client()

@app.route("/cluster", methods=["POST"])
def cluster():
    data = request.get_json(silent=True)
    if not data or "blockId" not in data:
        return jsonify({"error": "blockId required"}), 400

    block_id = data["blockId"]

    # prevent Firestore path injection
    if not isinstance(block_id, str) or "/" in block_id or block_id.strip() == "":
        return jsonify({"error": "invalid blockId"}), 400

    block = db.document(f"blocks/{block_id}").get()

    if not block.exists:
        return jsonify({"error":"not found"}),404

    members = block.to_dict().get("members",[])
    users = []

    users = []
    dim = None
    
    for uid in members:
        snap = db.document(f"users/{uid}").get()
        if not snap.exists:
            continue
    
        soft = snap.to_dict().get("soft")
    
        # must be a list
        if not isinstance(soft, list):
            continue
    
        # first valid vector defines dimension
        if dim is None:
            dim = len(soft)
    
        # must match dimension
        if len(soft) != dim:
            continue
    
        users.append((uid, soft))

    if len(users) < 2:
        return jsonify({"skipped":True})

    ids = [u[0] for u in users]
    try:
        X = np.array([u[1] for u in users], dtype=float)
    except:
        return jsonify({"error": "invalid feature vectors"}), 400
    
    # reject NaN and infinity
    if not np.isfinite(X).all():
        return jsonify({"error": "NaN or infinite values in features"}), 400
    
    X = StandardScaler().fit_transform(X)
    k = min(3,len(X))
    model = KMeans(n_clusters=k,n_init=10).fit(X)
#For KMeans, can adjust k (number of small groups within blocks), n_init (number of tries before starting groups), max_iter, feature weighting (done before KMeans)
#Feature weighting example: X[:,7] *= 2 when budget matters more
    cref = db.document(f"blocks/{block_id}").collection("clusters")
    for d in cref.stream():
        d.reference.delete()

    for i,uid in enumerate(ids):
        label = str(model.labels_[i])
        cref.document(label).set({
          "members": firestore.ArrayUnion([uid]),
          "centroid": model.cluster_centers_[int(label)].tolist()
        }, merge=True)

    return jsonify({"ok":True})
