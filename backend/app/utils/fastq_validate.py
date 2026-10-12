"""
Real FASTQ parsing and quality control — no simulated numbers.

A FASTQ record is 4 lines: @header, sequence, +, quality string (Phred+33
ASCII encoding, same convention Illumina/most sequencers use). This module
parses that format directly and computes genuine QC statistics: average
Phred quality per read, exact-duplicate detection, minimum-length
filtering, and a placeholder contaminant screen.

The contaminant screen is intentionally simple (substring match against a
small list of known host-DNA motifs) — a real pipeline would BLAST/Kraken2
against an actual host reference genome, which needs gigabytes of reference
data and its own service (see docs/architecture.md, section 3 "Preprocess").
This gives a real, working signal on the same shape of report without that
dependency.
"""
from dataclasses import dataclass, field
from typing import List


# Placeholder host-DNA motifs a contaminant screen would filter out (e.g.
# leftover human/host tissue DNA in an eDNA water sample). Real motifs would
# come from a downloaded host reference, not be hardcoded like this.
KNOWN_CONTAMINANT_MOTIFS = [
    "GATCACAGGTCTATCACCCTATTAACCACTCACGGGAG",  # human mtDNA-like motif (illustrative)
    "TTCTTTCATGGGGAAGCAGATTTGGGTACCACCC",       # illustrative host motif
]

MIN_LENGTH_DEFAULT = 100
MIN_AVG_QUALITY_DEFAULT = 20  # Phred score; 20 = 99% base-call accuracy


@dataclass
class FastqRecord:
    header: str
    sequence: str
    quality: str


@dataclass
class ValidationResult:
    total_sequences: int = 0
    passed_quality_filtering: int = 0
    duplicates_removed: int = 0
    contaminant_removed: int = 0
    below_length_excluded: int = 0
    remaining_after_filtering: int = 0
    warnings: List[str] = field(default_factory=list)


def parse_fastq(text: str) -> List[FastqRecord]:
    """Parses raw FASTQ text into records. Tolerant of trailing blank lines
    and \\r\\n line endings; raises ValueError on a genuinely malformed file
    (line count not a multiple of 4, or a record missing its '+' separator)."""
    lines = [l.rstrip("\r\n") for l in text.splitlines() if l.strip() != ""]

    if len(lines) % 4 != 0:
        raise ValueError(
            f"Malformed FASTQ: {len(lines)} non-blank lines isn't a multiple of 4 "
            "(each record needs @header, sequence, +, quality)."
        )

    records = []
    for i in range(0, len(lines), 4):
        header, seq, plus, qual = lines[i], lines[i + 1], lines[i + 2], lines[i + 3]
        if not header.startswith("@"):
            raise ValueError(f"Malformed FASTQ at line {i+1}: expected '@header', got '{header[:40]}'")
        if not plus.startswith("+"):
            raise ValueError(f"Malformed FASTQ at line {i+3}: expected '+' separator, got '{plus[:40]}'")
        if len(seq) != len(qual):
            raise ValueError(
                f"Malformed FASTQ at line {i+2}: sequence length ({len(seq)}) "
                f"doesn't match quality string length ({len(qual)})"
            )
        records.append(FastqRecord(header=header, sequence=seq.upper(), quality=qual))
    return records


def phred_quality_scores(quality: str) -> List[int]:
    """Decodes a Phred+33 quality string into per-base integer scores."""
    return [ord(ch) - 33 for ch in quality]


def average_quality(quality: str) -> float:
    scores = phred_quality_scores(quality)
    return sum(scores) / len(scores) if scores else 0.0


def is_contaminant(sequence: str) -> bool:
    return any(motif in sequence for motif in KNOWN_CONTAMINANT_MOTIFS)


def validate_fastq(
    text: str,
    min_length: int = MIN_LENGTH_DEFAULT,
    min_avg_quality: float = MIN_AVG_QUALITY_DEFAULT,
) -> ValidationResult:
    records = parse_fastq(text)
    result = ValidationResult(total_sequences=len(records))

    if not records:
        result.warnings.append("File contained no sequences.")
        return result

    seen_sequences = set()
    surviving: List[FastqRecord] = []

    for rec in records:
        if rec.sequence in seen_sequences:
            result.duplicates_removed += 1
            continue
        seen_sequences.add(rec.sequence)

        if is_contaminant(rec.sequence):
            result.contaminant_removed += 1
            continue

        if len(rec.sequence) < min_length:
            result.below_length_excluded += 1
            continue

        avg_q = average_quality(rec.quality)
        if avg_q < min_avg_quality:
            continue  # failed quality, not counted as "passed"; still excluded below

        result.passed_quality_filtering += 1
        surviving.append(rec)

    result.remaining_after_filtering = len(surviving)

    if result.total_sequences and result.remaining_after_filtering / result.total_sequences < 0.5:
        result.warnings.append(
            "Over half of all sequences were filtered out — check sequencer output quality "
            "or whether min_length/min_avg_quality thresholds fit this run."
        )
    if result.contaminant_removed > 0:
        result.warnings.append(
            f"{result.contaminant_removed} sequence(s) matched known contaminant motifs "
            "and were removed. This is a placeholder screen — see docs/architecture.md."
        )

    return result
