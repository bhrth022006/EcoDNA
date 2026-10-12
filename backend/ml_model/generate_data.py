"""
Generates a SYNTHETIC reference dataset for training the demo classifier.

This is NOT real GenBank/BOLD sequence data. Each species is assigned a
distinctive underlying "motif" sequence, then many noisy samples are
generated from it (random point mutations) so a k-mer frequency model has
real, learnable signal to train on. Swap this out for actual downloaded
reference barcodes (e.g. COI sequences from BOLD/NCBI) when you're ready
to move from demo to production.
"""
import random
import csv

random.seed(42)

BASES = "ACGT"

SPECIES = [
    "Cyprinus carpio", "Salmo trutta", "Anguilla anguilla", "Rana temporaria",
    "Bufo bufo", "Anas platyrhynchos", "Baetis rhodani", "Libellula depressa",
    "Procambarus clarkii", "Hydropsyche pellucidula", "Unio pictorum",
    "Viviparus viviparus", "Corbicula fluminea", "Tubifex tubifex",
    "Navicula cryptocephala", "Cymbella affinis", "Nostoc commune",
    "Microcystis aeruginosa",
]

SEQ_LEN = 200
MUTATION_RATE = 0.06      # fraction of bases randomly changed per sample
SAMPLES_PER_SPECIES = 60  # training examples per species


def random_seq(length):
    return "".join(random.choice(BASES) for _ in range(length))


def mutate(seq, rate):
    seq = list(seq)
    for i in range(len(seq)):
        if random.random() < rate:
            seq[i] = random.choice(BASES)
    return "".join(seq)


def main():
    rows = []
    for species in SPECIES:
        motif = random_seq(SEQ_LEN)  # each species' "true" underlying sequence
        for _ in range(SAMPLES_PER_SPECIES):
            sample = mutate(motif, MUTATION_RATE)
            rows.append((species, sample))

    random.shuffle(rows)
    with open("data/reference_sequences.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["species", "sequence"])
        w.writerows(rows)

    print(f"Wrote {len(rows)} sequences across {len(SPECIES)} species to data/reference_sequences.csv")


if __name__ == "__main__":
    main()
