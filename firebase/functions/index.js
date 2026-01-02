function genderBlocks(u) {
  const b = [];
  if (u.gender_pref.includes("same")) {
    if (u.gender === 1) b.push("M");
    if (u.gender === 2) b.push("F");
    if (u.gender === 3) b.push("NB");
  }
  if (u.gender_pref.includes("opposite")) b.push("C");
  return b;
}

function petBlocks(u) {
  const b = [];
  if (u.has_pet === 1) b.push("P");
  else b.push("N");
  if (u.pet_ok === 1) b.push("A");
  return b;
}

function computeBlocks(u) {
  const keys = [];
  for (const h of u.housing)
    for (const r of u.roommates)
      for (const g of genderBlocks(u))
        for (const p of petBlocks(u))
          keys.push(`${h}|${r}|${g}|${p}`);
  return keys;
}

exports.onUserWrite = functions.firestore
.document("users/{uid}")
.onWrite(async (change, context) => {
  const uid = context.params.uid;
  const after = change.after.data();
  const before = change.before.data() || {};

  const oldBlocks = before.blocks || [];
  const newBlocks = computeBlocks(after);

  const db = admin.firestore();
  const batch = db.batch();

  for (const b of oldBlocks)
    batch.update(db.doc(`blocks/${b}`), {
      members: admin.firestore.FieldValue.arrayRemove(uid)
    });

  for (const b of newBlocks)
    batch.set(db.doc(`blocks/${b}`), {
      members: admin.firestore.FieldValue.arrayUnion(uid),
      updatedAt: admin.firestore.FieldValue.serverTimestamp()
    }, {merge:true});

  batch.update(db.doc(`users/${uid}`), {blocks: newBlocks});
  await batch.commit();

  for (const b of newBlocks) {
    await fetch("https://YOUR-CLOUD-RUN-URL/cluster", {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ blockId: b })
    });
  }
});
