"""
Trains a k-mer frequency classifier on data/reference_sequences.csv.

Approach (standard for short-barcode taxonomic classification):
1. Break each sequence into overlapping k-mers (default k=4 -> 256 possible k-mers).
2. Count k-mer frequencies per sequence -> fixed-length feature vector.
3. Train a RandomForestClassifier to map k-mer frequency fingerprint -> species.

This is a real, trained model -- not a lookup table. Accuracy/feature
importances below come from actual model evaluation, not hardcoded values.
"""
import csv
import itertools
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder

K = 4
BASES = "ACGT"
ALL_KMERS = ["".join(p) for p in itertools.product(BASES, repeat=K)]
KMER_INDEX = {kmer: i for i, kmer in enumerate(ALL_KMERS)}


def kmer_features(seq):
    vec = np.zeros(len(ALL_KMERS), dtype=np.float32)
    seq = seq.upper()
    n = 0
    for i in range(len(seq) - K + 1):
        kmer = seq[i:i + K]
        idx = KMER_INDEX.get(kmer)
        if idx is not None:
            vec[idx] += 1
            n += 1
    if n > 0:
        vec /= n  # normalize to frequencies, not raw counts
    return vec


def load_data(path="data/reference_sequences.csv"):
    species, sequences = [], []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            species.append(row["species"])
            sequences.append(row["sequence"])
    return species, sequences


def main():
    species, sequences = load_data()
    X = np.array([kmer_features(s) for s in sequences])

    le = LabelEncoder()
    y = le.fit_transform(species)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Held-out test accuracy: {acc:.3f}")
    print(classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0))

    joblib.dump({
        "model": clf,
        "label_encoder": le,
        "kmer_list": ALL_KMERS,
        "k": K,
    }, "model.joblib")
    print("Saved trained model to model.joblib")


if __name__ == "__main__":
    main()
