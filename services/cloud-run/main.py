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
    block_id = request.json["blockId"]
    block = db.document(f"blocks/{block_id}").get()

    if not block.exists:
        return jsonify({"error":"not found"}),404

    members = block.to_dict().get("members",[])
    users = []

    for uid in members:
        snap = db.document(f"users/{uid}").get()
        if snap.exists and "soft" in snap.to_dict():
            users.append((uid,snap.to_dict()["soft"]))

    if len(users) < 2:
        return jsonify({"skipped":True})

    ids = [u[0] for u in users]
    X = np.array([u[1] for u in users])

    X = StandardScaler().fit_transform(X)
    k = min(3,len(X))
    model = KMeans(n_clusters=k,n_init=10).fit(X)

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
